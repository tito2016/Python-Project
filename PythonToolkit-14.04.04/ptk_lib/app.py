"""
The main python toolkit application.
"""
#---Logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import __main__         #access to the main namespace
import os.path          #path operations
import sys              #access sys arguments
import imp              #package checking
import wx               #gui libary

#import the aui libary and store under the main app level for all tools to use
#this makes it easy to switch to pyaui if necessary
import wx.aui as aui

import ptk_lib
from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus.wx_message_bus import wxMessageBus
from ptk_lib import misc
from ptk_lib.misc import USERDIR, TOOLDIR, RESOURCE_DIR

from ptk_lib.resources import splash
from ptk_lib import tool_manager       #plugins/tools management

#Core tools
from ptk_lib.core_tools import taskicon         #taskbar/settings icon tool
from ptk_lib.core_tools import fileio           #file import and export system

from ptk_lib.core_tools import console          #main console window
from ptk_lib.core_tools import editor           #editor tool

from ptk_lib.core_tools import views            #GUI views of python objects
from ptk_lib.core_tools import pathman          #python path management tool
from ptk_lib.core_tools import nsbrowser        #namespace browser
from ptk_lib.core_tools import inspector        #object inspection tool
from ptk_lib.core_tools import cmdhistory       #command history viewer

from ptk_lib.core_tools import numpy_pack       #numpy module extensions

#---main application class------------------------------------------------------
class PTKApp(wx.App):
    """ The main PTK application class """

    def __init__(self, name, args):
        """
        Create the PTK app
        """
        self.args = args
        wx.App.__init__(self, redirect=False, clearSigInt=False)
        self.SetAppName(name)       #set app name

    def OnInit(self):
        """
        Called by wx libary when creating app should return True/False
        """
        #get arguments
        debug = self.args.get('debug', False)     #get debug level
        files = self.args.get('files', [])        #get files to edit
        
        #check if another is running?
        self.imon = wx.SingleInstanceChecker('PTK-lock', misc.USERDIR) 
        if self.imon.IsAnotherRunning():
            #change log to not overwrite already running instance
            if debug:
                LOGLEVEL = misc.DEBUG
            else:
                LOGLEVEL = misc.WARNING # DEBUG,INFO,WARNING,ERROR
            misc.setup_log(filename=None, level=LOGLEVEL)

            #load the messenger port from settings
            cfg = misc.get_config()
            cfg.SetPath("App//")
            port = cfg.ReadInt("message_bus_port", 6666)

            #create a client messenger to communicate with running instance
            from ptk_lib.message_bus.mb_client import MBClient
            msg_client = MBClient(name='PTK second instance')
            msg_client.connect('localhost', port)
                
            #send a message with the files to open
            #convert to absolute paths
            data = []
            for file in files:
                data.append(os.path.abspath(file))
            msg_client.send_msg('App', 'NewInstance', (data,))

            #now close and exit
            msg_client.disconnect()
            return False
        
        #setup log
        LOGFILE  = misc.USERDIR + 'ptk_debug.log'
        if debug:
            LOGLEVEL = misc.DEBUG
        else:
            LOGLEVEL = misc.INFO # DEBUG,INFO,WARNING,ERROR
        misc.setup_log(filename=LOGFILE, level=LOGLEVEL)

        #---Show a splash screen -----------------------------------------------
        bmp = splash.splash.GetBitmap()
        splashscreen = wx.SplashScreen(bmp, wx.SPLASH_CENTRE_ON_SCREEN| wx.SPLASH_NO_TIMEOUT, 10000, None, -1)
        splashscreen.Show()

        #---Start the Message Bus ----------------------------------------------
        log.info('Starting MessageBus')
        self.msg_bus = wxMessageBus(name='PTK', timeout=10)
        
        #load the messenger port from settings
        cfg = self.GetConfig()
        cfg.SetPath("app//")
        port = cfg.ReadInt("message_bus_port",6666)

        try:
            self.msg_bus.start_server(port=port, allow_ext=False)
        except:
            log.exception('Failed to start message bus server on port:'+str(port))
            log.info('Trying to start message service on port:'+str(port+1))
            self.msg_bus.start_server(port=port+1, allow_ext=False)

        #update the ptk_script_path option to allow apps with embedded engines
        # to start PTK via engine.eng_misc.start_PTK()
        cfg.Write('ptk_script_path', sys.argv[0])

        #create a messagebus node for the application
        self.msg_node = MBLocalNode('App')
        self.msg_node.connect(self.msg_bus)
        self.msg_node.set_handler('NewInstance', self.msg_new_instance) 

        #initialise tool plugin system -----------------------------------------   
        log.info('Starting Toolmanager')
        self.toolmgr = tool_manager.ToolManager(TOOLDIR)
       
        #Start core tools ------------------------------------------------------
        log.info('Starting core tools')

        #top level tools - need to be started in the correct order
        self.toolmgr.start_tool('TaskIcon')         #first for console/editor menu items
        self.toolmgr.start_tool('FileIO')           #before editor for editor importer
        self.toolmgr.start_tool('Console')          
        self.toolmgr.start_tool('Editor')           #after fileIO to add importer

        #other tools doesn't really matter about the order.
        self.toolmgr.start_tool('Views')
        self.toolmgr.start_tool('PathManager')
        self.toolmgr.start_tool('NSBrowser')
        self.toolmgr.start_tool('CmdHistory')
        self.toolmgr.start_tool('Inspector')

        #module packs
        try:
            imp.find_module('numpy')
            self.toolmgr.start_tool('NumPy Pack')
        except:
            log.info('Numpy not found - skipping loading tool - NumPy Pack')
        log.info('Done loading core tools')

        #start the user tools -------------------------------------------------
        log.info('Starting user tools')
        self.toolmgr.load_settings()     #load other tools
        log.info('Done loading user tools')

        #Publish app.init message ---------------------------------------------
        log.info('Application init done - publishing App.Init message')    
        self.msg_node.publish_msg('App.Init',())

        #process any input arguments ------------------------------------------
        wx.CallAfter(self.ProcessInputArgs, files)

        #close splash screen---------------------------------------------------
        wx.CallAfter(splashscreen.Close)

        return True
        

    #---------------------------------------------------------------------------    
    def ShowTips(self, override=False):
        config = self.GetConfig()
        config.SetPath("App//")
        showtip = config.ReadBool("show_tips",True)
        tip_n   = config.ReadInt("tip_n",0)

        if showtip or override:
            tp = wx.CreateFileTipProvider( RESOURCE_DIR+"tips.txt", tip_n)
            showtip = wx.ShowTip(None, tp, showtip)
            tip_n = tp.GetCurrentTip()
            config.WriteBool("show_tips", showtip)
            config.WriteInt("tip_n", tip_n)
            config.Flush()

    def GetConfig(self):
        """
        Return the application wxConfig object
        """
        cfg = wx.FileConfig(localFilename=USERDIR+'options')
        return cfg

    def ProcessInputArgs(self,files=[]):
        """
        Process the system arguments from this instance or a second instance 
        sent via messenger
        """
        log.info('Processing input filepaths: '+str(files))
        if files == []:
            #if no files to open i.e. == [] show the console window
            self.msg_node.send_msg('Console', 'Show',())
            wx.CallAfter(self.ShowTips)
        else:
            #open the files
            self.msg_node.send_msg('Editor','Open',files)

    def VetoExit(self):
        """
        Prevent an imminent application exit
        """
        self.exit_veto = True

    def Exit(self):
        """
        Exit the application
        """
        log.info('Application exit request')

        #Send exitcheck to ensure it is ok to exit - listeners call app.VetoExit
        # to prevent application exit.
        log.info('Preforming exit check') 
        self.exit_veto = False
        self.msg_node.publish_msg('App.ExitCheck',())
        wx.YieldIfNeeded()
        if self.exit_veto is True:
            log.info('Exit vetoed')
            return
      
        #send application exit message - any listeners can do exit tasks
        log.info('Continuing with exit, sending exit message')
        self.msg_node.publish_msg('App.Exit',())
        wx.YieldIfNeeded()
        
        #shutdown toolmanager
        self.toolmgr.shutdown()

        #shutdown messenger
        self.msg_bus.shutdown()

        #and exit
        log.info('Actually exiting now')
        self.imon = None
        logging.shutdown()
        wx.App.Exit(self)

    #---message handlers--------------------------------------------------------
    def msg_new_instance(self,msg):
        """
        Called with the input arguments to a second instance - the sending
        instance then closes.
        """
        files, = msg.get_data()
        log.info('Second instance was started, files were: '+str(files))
        if len(files) != 0:
            self.ProcessInputArgs(files)
