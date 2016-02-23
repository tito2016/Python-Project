"""
The PathManager core tool 

Core tool providing a pathlist to set the current working directory and a dialog
to edit the python search paths (sys.path).
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.INFO)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui
import os

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode

from pathman_ctrls import PathManTools             
import pathman_icons                                  

#---the tools class-------------------------------------------------------------
class PathManager(Tool):
    name = 'PathManager'
    descrip = 'Core tool providing a pathlist to set the current working directory and a dialog to edit the python search paths.'
    author = 'T.Charrett'
    requires = ['Console']
    core = True            
    icon = pathman_icons.pathmanager32

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('PathManager')
        self.msg_node.connect(self.msg_bus)

        #subscribe to messages
        self.msg_node.subscribe('App.Init',self.msg_app_init)
        self.msg_node.subscribe('App.Exit',self.msg_app_exit)
        
        #create a toolbar in the console window
        console = self.toolmgr.get_tool('Console')
        self.tb = PathManTools(console.frame, self)
        pane = (aui.AuiPaneInfo().Name('PathManager')
                    .Caption('PathManager').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(0).Position(1).LeftDockable(False)
                    .RightDockable(False))
        console.frame.AddToolbar( self.tb, 'PathManager', pane,
                            helpstring = 'Show/Hide the PathManager toolbar')

        log.info('Done Initialising tool')

    #---Message handlers--------------------------------------------------------
    def msg_app_init(self,msg):
        """
        On application start load the settings
        """
        #Load the recent working directory list
        self.tb.pathlist.LoadPaths()

        #get the stored system paths
        # How - have a seperate list with paths added automatically to all 
        # new engines?

        #add them if not already in sys.path
        
    def msg_app_exit(self,msg):
        """
        On application exit save the settings
        """
        #save the recent working directory list
        self.tb.pathlist.SavePaths()

        #store the sys.paths?
        #TODO:
