"""
Main console tool
-----------------

The matlab style main window and console/engine management.

Console are controls added to the cosole frames main pane - examples would be
interactive python consoles (engines), running processes input/output terminals 
etc. This allows multiple python interpreters/engines to be active with the tool
keeping track of active engine consoles and associatated processes.


About engines/consoles:
----------------------
Engines have a unique name (engname) which is also their messagebus nodename. 
This starts with 'Engine.' and is assigned automatically when an engine connects
to the message bus.

For each engine node a console node is created which controls the engine (this 
has a unique name which starts 'Console.'.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import __future__		        #for engine compiler flags
import threading                #used for lock for engine names
import os                       #for launching external engines
import subprocess               #for launching external engines
import sys                      #for launching external engines
import pickle					#for reading startup options

import wx

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus import mb_protocol
from ptk_lib.engine import eng_messages
from ptk_lib.engine import eng_misc
from ptk_lib.engine.internal_engine import InternalEngine
from ptk_lib.resources import common16

#console components
from console_frame import ConsoleFrame
from console_settings import ConsoleSettingsPanel
from console_settings import AutostartPanel, EnvironmentPanel
import console_messages
import console_icons

from engine_page import EnginePageBase, EngPageSTC
from script_page import ScriptPage

#-------------------------------------------------------------------------------
#Find the engine launch script
#installs on linux/max will use PTKengine with the .pyw extension.
#-------------------------------------------------------------------------------
PTKengine_PATH = os.path.abspath( os.path.dirname(sys.argv[0]) )+os.sep+'PTKengine'
if sys.argv[0].endswith('.pyw'):
    PTKengine_PATH = PTKengine_PATH + '.pyw'

#---the tools class-------------------------------------------------------------
class Console(Tool):
    name = 'Console'
    descrip = 'Core tool implementing the main console window and engine management'
    author = 'T.Charrett'
    requires = ['TaskIcon']           
    core = True            
    icon = console_icons.console32
    
    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('Console')
        self.msg_node.connect(self.msg_bus)
        
        #Register message handlers for console tool messages
        self.msg_node.set_handler(console_messages.CONSOLE_SHOW, self.msg_show)
        self.msg_node.set_handler(console_messages.CONSOLE_HIDE, self.msg_hide)

        #subscribe to application messages
        self.msg_node.subscribe('App.Init', self.msg_app_init)
        self.msg_node.subscribe('App.Exit', self.msg_app_exit)

        #-----------------------------------------------------------------------
        # GUI parts
        #-----------------------------------------------------------------------
        #create the console frame
        self.frame = ConsoleFrame(self)

        #Add taskbar menu item
        taskicon = self.toolmgr.get_tool('TaskIcon')
        bmp = console_icons.console16.GetBitmap()
        taskicon.add_menu_item( wx.NewId(), 'Open the Console',
                                'Open the Console window', 
                                self.on_show, bitmap=bmp)  

        #Add console settings panel
        taskicon.add_settings_item( 'Console', None, 
                                    console_icons.console16.GetBitmap())
        taskicon.add_settings_item( 'Console\\Display', ConsoleSettingsPanel)

        #add enginemanager settings panels
        taskicon.add_settings_item( 'Console\\Startup engines', AutostartPanel,
                                    None)
        taskicon.add_settings_item( 'Console\\Python environment', 
                                    EnvironmentPanel, None)

        #-----------------------------------------------------------------------
        # engine management parts
        #-----------------------------------------------------------------------

        #for generating unique ids - locked as MessageBus will call back to get
        # an id for connecting engines from the comms thread
        self.id_lock = threading.Lock()
        self.id_counter = 0

        #internal engine instance
        self.internal = None

        #Dictionaries of active engines
        self.eng_processes = {} #(engid: subprocess process object}

        #find which engines are available
        self.engtypes = []       #list of engtypes strings
        self.engdescrip = {}     #engtype string, description string
        self.engtypes, self.engdescrip = eng_misc.get_available_engines()

        #subscribe to MessageBus messages to make sure we know if an 
        #engine connects or disconnects
        self.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                self.msg_sys_connect)  
        self.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                self.msg_sys_disconnect)  

        #set the callable to provide nodes names for connecting 'Engine:*'
        self.msg_bus.register_node_group('Engine', self._new_engine_name)

        log.info('Done Initialising tool')

    #---Interfaces--------------------------------------------------------------
    def show_console(self):
        """
        Show the Console frame
        """
        self.frame.Show()
        self.frame.Raise()

    def hide_console(self):
        """
        Hide the console frame
        """
        self.frame.Hide()

    def add_menu_item(self, menu, id, string, helpstring, evthndlr, bitmap=None,
                        pos=None):
        """
        Add a menu item to the menu.
            menu - string description of menu ('Tools', 'File'. 'Edit' etc)
            string - string to display
            helpstring - help string for item
            evthndlr - wx event handler callable
            bitmap  - bitmap to use / None for no bitmap
            pos - Position in menu, inserted here if specified.
        """
        menu = self.frame.GetMenu(menu)
        item = wx.MenuItem(menu, id, string,helpstring)
        self.frame.Bind(wx.EVT_MENU, evthndlr, id=id)
        if bitmap is not None:
            item.SetBitmap(bitmap)
        if pos is None:
            pos = menu.GetMenuItemCount()
        menu.InsertItem(pos,item)

    def get_current_console(self):
        """
        Get the current active console. If there are no consoles, None is 
        returned.
        
        See get_engine_console/get_current_engine to retrieve only engine 
        consoles.
        """
        return self.frame.GetCurrentConsole()

    #---engines-----------------------------------------------------------------
    #engine starting/closing
    def _new_engine_name(self):
        """
        Returns a new unqiue engine name.
        """
        with self.id_lock:
            id = self.id_counter
            self.id_counter = self.id_counter + 1
        
        return 'Engine.'+str(id)
        
    def start_engine(self, engtype, englabel, filepath=None, debug=False):
        """
        Start a new engine. 

        This creates the Engine message bus node (either by creating the 
        InternalEngine object or launching an external process which connects to
        the message bus). 

        The EngineConsole is not created until the EngineNode has actually 
        connected (see msg_eng_connect).
        """
        log.info('Starting engine: '+engtype+' label: '+englabel)

        #check engtype is available
        if engtype not in self.engtypes:
            raise Exception('Unknown/Unavailable engine type: '+str(engtype))

        #Now start the engine
        if engtype=='Internal':
            self.internal = InternalEngine( userdict={}, doyield=wx.YieldIfNeeded)
            port = str(self.msg_bus.server.get_port())
            self.internal.connect( 'localhost', port)
            engname = 'Engine.'+str(os.getpid())
        else:

            #check the message bus has a server running
            if self.msg_bus.has_server() is False:
                self.msg_bus.start_server()

            port = str(self.msg_bus.server.get_port())

            #construct args
            args = [PTKengine_PATH , engtype[:-6]]
    
            #add label
            if englabel is not None:
                args.append(englabel)
 
            #add connect args
            args.extend(['-c','localhost',port])
    
            #add optional file arg
            if filepath is not None:
                log.debug('filepath:'+filepath)
                args.extend( ['-f', filepath] )

            #add debug mode
            if debug is True:
                args.append('-d')

            #need to add the python executable for windows
            if sys.platform=='win32':
               args = [sys.executable]+args
            
            #launch process
            #todo: get pipes for stderr/stdout 
            # to push c stdIO to the console after each command.
            log.debug('Launch args: '+str(args) )
            process = subprocess.Popen(args,shell=False)

            #store process in dictionary to clear up when the engine ends
            engname = 'Engine.'+str(process.pid)

            self.eng_processes[engname] = process

        log.debug('Engine launched '+engname+', '+engtype)

    def close_engine(self, engname):
        """
        Close the engine with the node name given.
        """
        if self.msg_bus.has_node(engname) is False:
            raise Exception('No engine (and mbnode) with name: '+engname)

        #close the engine
        self.msg_bus.close_node(engname)
        #This requests the engine to close, the console interface is removed 
        #when the engine disconnects from the message bus

    def kill_engine(self, engname):
        """
        Kill the engine given by engname if possible
        """
        eng = self.get_engine_console( engname )
        eng.kill()
        
    def get_engine_console(self, engname):
        """
        Get the engine console for the given engine node name, engname.

        If there is no engine consoles for the given engine name, None will be 
        returned.
        Note the engine console for a given engine name may not be active
        (check the is_interactive flag).
        """
        engconsoles = self.frame.GetConsoles(EnginePageBase)
        for con in engconsoles:
            if con.engine == engname:
                return con
        return None
        
    def get_all_engines(self, active=True):
        """
        Get all engine consoles.
        If active is True only return interactive engine consoles.
        If active is False return all engine consoles.
        """
        engconsoles = self.frame.GetConsoles(EnginePageBase)
        if active is False:
           return engconsoles
        
        active=[]
        for con in engconsoles:
            if con.is_interactive is True:
               active.append(con)
        return active
        
    def get_engine_names(self, active=True):
        """
        Get all the engine names.
        If active is True only return interactive engine consoles.
        If active is False return all engine consoles.
        """
        engconsoles = self.frame.GetConsoles(EnginePageBase)
        if active is False:
            names = []
            for con in engconsoles:
                names.append(con.engine)
        else:
            names = []
            for con in engconsoles:
                if con.is_interactive is True:
                   names.append(con.engine)
        return names
        
    def get_engine_labels(self, active=True):
        """
        Get all active engine labels (the name displayed to the user rather than
        the engname which is a unique id/message bus node name.
        If active is True only return interactive engine consoles labels
        If active is False return all engine consoles labels.
        """
        engconsoles = self.frame.GetConsoles(EnginePageBase)
        if active is False:
            labels = []
            for con in engconsoles:
                labels.append(con.englabel)
        else:
            labels = []
            for con in engconsoles:
                if con.is_interactive is True:
                   labels.append(con.englabel)
        return labels

    def get_current_engine(self):
        """
        Get the current engine console. 

        Returns None if there is no engine consoles, or if the current console 
        is not an engine console or if the current engine console is not active.
        """
        console = self.frame.GetCurrentConsole()

        #check if an engine and connected
        if console is None:
            is_engine = False
        else:
            is_engine = console.is_interactive

        #not an active engine
        if is_engine is False:
            return None

        return console
        
    def is_engine_current(self, engname):
        """
        Check if the engname given is the current active console
        """
        eng = self.get_current_engine()
        if eng.engine == engname:
            return True
        return False
        
    def get_engine_types(self):
        """
        Get a dict of available engine types.
        """
        #return a copy of the types list.
        return list(self.engtypes)

    def get_engine_descriptions(self):
        """
        Get a dict of available engine types : engine description
        """
        #return a copy of the global.
        return dict(self.engdescrip)
        
    def exec_source(self, engname, source):
        """
        Execute source in the current engines console as if it where entered at 
        the console.
        """
        console = self.get_engine_console( engname )
        if console is None:
            return

        #show the window
        if self.frame.IsShown() is False:
            self.frame.Show()
        if self.frame.IsIconized():
            self.frame.Restore()
        self.frame.Raise()

        #exec source in the console
        console.exec_source(source)

    def exec_file(self, filepath, engname=None):
        """
        Execute a file of source as if enetering >>> execfile(filepath) at the 
        console.
        """
        if engname is None:
            console = self.get_current_engine()
        else:
            console = self.get_engine_console( engname )
        if console is None:
            return

        #show the window
        if self.frame.IsShown() is False:
            self.frame.Show()
        if self.frame.IsIconized():
            self.frame.Restore()
        self.frame.Raise()

        #execfile in the console
        console.exec_file(filepath)

    #---script consoles---------------------------------------------------------
    def run_script(self, filepath, args):
        """ 
        Run a script and add a script console to the console notebook.
        """
        con = ScriptPage(self.frame.book)
        self.frame.AddConsole( con, filepath, common16.pythonfile16.GetBitmap() )
        con.StartProcess(filepath, args)

        #set the new script console as current
        self.frame.SetCurrentConsole(con)

    #---message handlers--------------------------------------------------------
    def msg_show(self, msg):
        """
        Message handler to show the console frame
        """
        self.frame.Show()
        self.frame.Raise()

    def msg_hide(self, msg):
        """
        Message handler for Console.Hide
        """
        self.frame.Hide()

    def msg_app_init(self, msg):
        """
        Listener for App.Init message
        Sent when application starts
        """
        #autostart engines and setup defualt environment
        cfg = self.app.GetConfig()
        cfg.SetPath("Console//")
        s = cfg.Read("auto_start_engines","")  #a list of engine name, type tuples to autostart
		
        try:
            engs = pickle.loads(str(s))
        except:
            engs=[("Engine-1","wxEngine")]

        #start each engine
        log.info(str(engs))
        for englabel,engtype in engs:
            log.info('Auto starting engine '+str(englabel)) 
            eng = self.start_engine(engtype, englabel)

        #load the main window layouts (in aui mixin class)
        self.frame.LoadLayouts()

    def msg_app_exit(self, msg):
        """
        Listener for App.Exit message
        Save settings on application exit
        """
        #save the main window layouts (in aui mixin class)
        self.frame.SaveLayouts()

        #Engines are closed automatically by the message_bus closing all 
        #connections, this avoids processing any unecessary messages when the
        #program is about to exit anyway
        
    def msg_sys_connect(self,msg):
        """
        Called when a new engine node connects
        Create a Console object to control it if necessary and then publish an 
        EngineStarted message.
        """
        nodename, = msg.get_data()
        log.info(   'New engine connected: '+nodename) 
                
        ##check if a console exists for this engine and create a new console as 
        ##necessary
        con = self.get_engine_console(nodename)
        if con is None:
            #No console exists for this engine (if one did it would take control
            #automagically. Need to create a new console.
            engnode = nodename
            
            #create a new console for this engine
            con = EngPageSTC(self.frame.book)
            self.frame.AddConsole(con, engnode)
            
            #set it to manage the new engine
            con.set_managed_engine(engnode)
            #wx.YieldIfNeeded()

        ##finally do other startup tasks
        #set up engine environment
        #execute startup script if option selected
        cfg = self.app.GetConfig()
        cfg.SetPath("EngineManager//")
        flag = cfg.ReadBool("exec_startup",True)
        if flag is True:
            res = con.run_task('execute_startup_script')
            log.debug('Startup script executed - success ='+str(res))

        #add builtin commands
        con.add_builtin(ptk_help, 'ptk_help')
        con.add_builtin(clear, 'clear')

        #set compiler flags
        flag = cfg.ReadBool("future_div",False)
        con.set_compiler_flag(__future__.CO_FUTURE_DIVISION,flag)
        flag = cfg.ReadBool("future_import",False)
        con.set_compiler_flag(__future__.CO_FUTURE_ABSOLUTE_IMPORT,flag)
        flag = cfg.ReadBool("future_print",False)
        con.set_compiler_flag(__future__.CO_FUTURE_PRINT_FUNCTION,flag)
        flag = cfg.ReadBool("future_unicode",False)
        con.set_compiler_flag(__future__.CO_FUTURE_UNICODE_LITERALS,flag)
        
        #set the new engine console as current
        self.frame.SetCurrentConsole(con)

    def msg_sys_disconnect(self, msg):
        """
        Called when an Engine node disconnects.
        """
        nodename = msg.get_data()[0]
        
        log.info('Engine disconnected, engname: '+nodename)
        #if internal engine - reset the self.internal attribure
        if nodename == 'Engine.Internal':
           self.internal = None

        #check if this was started by the Console tool and remove/comunicate 
        #with its process object to prevent orphaned processes.
        process = self.eng_processes.pop(nodename,None)

        if process is not None:
            #todo: start process with a pipe then read stdout/stderr and
            #print this to console here.
            process.poll() #communicate(None)

    #---others------------------------------------------------------------------
    def on_show(self, event):
        """wx event handler for taskbar menu item"""
        self.frame.Show()
        self.frame.Raise()

#-------------------------------------------------------------------------------
# Commands to add to engines
#-------------------------------------------------------------------------------
def ptk_help():
    """
    Display PTK specfic help
    """
    doc = (
    "Python Toolkit console keys:\n"+
    "   ctrl+up/down    -   cycle through command history\n"+
    "                       (searches for a partially typed command)\n"+
    "   escape          -   clear the current command\n"+
    "   ctrl+space      -   open the autocomplete list\n"+
    "\n"+
    "Engines:\n"+
    "The internal engine (python interpretor) runs in the same process as the\n"+
    "interface so if your program crashes or hangs so will PTK. Use an external\n"+
    "engine (a python interpretor in a separate process) to avoid blocking the \n"+
    "GUI when running long commands or when interactive use of a GUI mainloop \n"+
    "is required (wxPython can be used from the internal engine as well).\n"+
    "Multiple external engines can be used simutanously, but only a single \n"+
    "internal engine is allowed"
    )
    print doc

#-------------------------------------------------------------------------------
#Uses engine message CLEAR
def clear():
    """
    Clear the PTK console
    """
    #send a engine interface message to clear the console
    from __main__ import _engine
    _engine.send_msg(_engine.console, 'Con.Clear',())

