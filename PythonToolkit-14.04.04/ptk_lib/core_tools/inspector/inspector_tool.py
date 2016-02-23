"""
Inspector tool - adds a pane to the console window allowing object information to
be displayed.

Tools can customise the information shown for a type using the interface provided:

TODO: Add external interface / customisable inspector info
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus import mb_protocol

from ptk_lib.core_tools.console import console_messages
from ptk_lib.core_tools.nsbrowser import Action

import inspector_icons
from inspector_control import InspectorControl
import inspector_messages

#---the tool class--------------------------------------------------------------
class InspectorTool(Tool):
    name = 'Inspector'
    descrip = 'Tool providing an object information pane in the console window'
    author = 'T.Charrett' 
    requires = ['Console','NSBrowser']
    core = True
    icon = inspector_icons.inspector32

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')
        
        #create a message bus node for this tool
        self.msg_node = MBLocalNode('Inspector')
        self.msg_node.connect(self.msg_bus)

        #Register message listeners
        self.msg_node.set_handler(inspector_messages.SHOW, self.msg_show) 
        self.msg_node.set_handler(inspector_messages.INSPECT, self.msg_inspect) 
        
        self.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                self.msg_eng_connect)             

        self.console = self.app.toolmgr.get_tool('Console')

        ##create the inspector as a pane in the main window
        self.inspector = InspectorControl(self.console.frame, self)
        pane = aui.AuiPaneInfo()
        #setup how to display this panel
        name='Inspector'
        pane.Name(name) #id name
        pane.Caption(name) # caption
        pane.Right() #position
        pane.Layer(1)
        pane.Position(0)
        pane.Row(0)
        pane.CloseButton(True) #close button
        pane.MaximizeButton(True)
        pane.MinimizeButton(True)
        pane.Floatable(True)
        pane.BestSize( (350,400) )
        pane.MinSize( (350,300) )
        pane.DestroyOnClose(False)
        self.console.frame.auimgr.AddPane(self.inspector,pane)

        #add a menu item to the tools menu to show and hide our pane
        bmp = inspector_icons.inspector16.GetBitmap()
        self.console.add_menu_item('tools', wx.NewId(), 'Inspector', 
                    'Open the Inspector tool', self.on_show, bmp)

        #Register a type action with the NSBrowser
        nsbtool = self.toolmgr.get_tool('NSBrowser')
        nsbtool.register_type_action(InspectAction(self))

        log.info('Done Initialising tool')
    
    #---Interfaces--------------------------------------------------------------
    def inspect_object(self, engname, oname):
        """
        Show the object given by oname in the inspector pane.
        """
        self.inspector.SetAddress(oname, engname)
        #ensure the pane is shown
        pane=self.console.frame.auimgr.GetPane('Inspector')
        pane.Show()
        self.console.frame.auimgr.Update()

    def show(self):
        """
        Show the inspector pane
        """
        pane=self.console.frame.auimgr.GetPane('Inspector')
        pane.Show()
        self.console.frame.auimgr.Update()

    #---Message handlers--------------------------------------------------------
    def msg_show(self,msg):
        """
        Message handler for Inspector Show.
        Show the Inspector pane.
        """
        self.show()

    def msg_inspect(self,msg):
        """
        Message handler for Inspector Inspect
        message data is the object name, engine name to display
        """
        #show new object
        engname,oname = msg.get_data()
        self.inspect_object(engname,oname)

    def msg_eng_connect(self,msg):
        """
        When an engine is started add the inspect() command
        """
        log.debug('Adding inspect() command to new engine')
        engname, = msg.get_data()
        eng = self.console.get_engine_console(engname)
        eng.add_builtin(inspect, 'inspect')

    #---other-------------------------------------------------------------------
    def on_show(self, event):
        """
        wxMenu event handler for menu item.
        """
        pane=self.console.frame.auimgr.GetPane('Inspector')
        pane.Show()
        self.console.frame.auimgr.Update()


#-------------------------------------------------------------------------------
# Magic command
#-------------------------------------------------------------------------------
def inspect(objname):
    """
    Inspect the object in the inspector: objname should be a string!
    """
    import __main__
    #check name
    try:
        o = eval(objname,__main__._engine._userdict)
    except:
        raise NameError('Object name not found')
    #send engine message
    data = (__main__._engine.name, objname)
    __main__._engine.send_msg('Inspector','Inspect',data)
    
#-------------------------------------------------------------------------------
# NSBrowser action
#-------------------------------------------------------------------------------
class InspectAction(Action):
    def __init__(self, tool):
        Action.__init__(self, 'Inspect Object',
                            type_strings=[-1], 
                            helptip='Show the objects information in the Inspector',
                            multi=False )
        self.tool = tool

    def __call__(self, engname, obj_names):
        self.tool.inspect_object(engname,obj_names[0])
