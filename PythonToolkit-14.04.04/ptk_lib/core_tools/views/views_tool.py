"""
Views

A tool providing a common interface to open GUI views of python objects in engines.
"""     
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui

from ptk_lib.tool_manager import Tool
from ptk_lib.resources import ptk_icons

from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus import mb_protocol

from ptk_lib.engine import eng_messages
from ptk_lib.core_tools.console import console_messages

import view_messages
import type_views

#---the tools class-------------------------------------------------------------
class ViewsTool(Tool):
    name = 'Views'
    descrip = 'Core tool providing a common interface to GUI views of python objects'  
    author = 'T.Charrett' 
    requires = ['Console']
    core = True
    icon = None

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #views - dictionary of {otype:view}
        self.viewdict = {}
        self._register_default_type_views()

        #viewer panes in console window to display object view
        #dictionary of open viewers { engname : {oname:viewer} }
        self.open_viewers = {}

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('Views')
        self.msg_node.connect(self.msg_bus)

        #Register message listeners
        self.msg_node.set_handler(view_messages.OPENVIEW, self.msg_open_view) 
        self.msg_node.set_handler(view_messages.HASVIEW,  self.msg_has_view) 

        #subcribe to these subjects
        self.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                self.msg_eng_connect)  
                                
        self.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine',
                                self.msg_eng_disconnect)  
                                
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_DONE, 
                                 self.msg_eng_change)
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_CHANGE, 
                                 self.msg_eng_change)

        #get a reference to the console tool
        self.contool = self.toolmgr.get_tool('Console')

        log.info('Done Initialising tool')

    def _register_default_type_views(self):
        """
        Add the standard views
        """
        self.set_type_view('__builtin__.str',type_views.StringView) #the string view
        self.set_type_view('__builtin__.unicode',type_views.StringView) #the string view
        self.set_type_view('__builtin__.list',type_views.ListView) #the list view
 
    #---Interfaces-------------------------------------------------------------- 
    def set_type_view(self,type_string,view):
        """
        Register a gui view for the object type, otype.
        Return True if ok, False if a view is already registered for that type.
        """
        #check if there is already a view for the type
        if self.viewdict.has_key(type_string):
            return False
        #add to the dict
        self.viewdict[type_string]=view
        return True

    def get_type_view(self,type_string):
        """
        Get the view for the object type_string.
        Returns None if no view is registered.
        """
        view = self.viewdict.get(type_string,None)
        return view

    def has_type_view(self,type_string):
        """
        Check if a view exists for the type
        """
        return self.viewdict.has_key(type_string)

    def open_viewer_pane(self,engname,oname):
        """
        Open a Viewer pane in the console window for the object and engine name
        given. If no view is registered the no view message is automatically 
        displayed by the viewer
        """
        if engname is None:
            eng = self.contool.get_current_engine()
            engname = eng.name

        #viewer already open
        eng_viewers = self.open_viewers.get(engname,{})
        if oname in eng_viewers.keys():
            return 

        #create the viewer panel
        vpanel = type_views.TypeViewer(self.contool.frame, self, oname,engname)
        eng_viewers[oname] = vpanel
        self.open_viewers[engname] = eng_viewers
        vpanel.Bind(wx.EVT_WINDOW_DESTROY,self.on_viewer_close,vpanel)

        #add the panel as a aui pane to the console window, initially floating
        name = 'View: '+oname+' ['+engname+']'
        pane = aui.AuiPaneInfo()

        #setup how to display this panel
        pane.Name(name)
        pane.Caption(name)
        pane.CloseButton(True) 
        pane.MaximizeButton(True)
        pane.MinimizeButton(True)
        pane.Floatable(True)
        pane.FloatingPosition((100,100))
        pane.Float()
        pane.BestSize( (300,200) )
        pane.MinSize( (200,130))
        pane.DestroyOnClose(True)

        self.contool.frame.auimgr.AddPane(vpanel,pane)
        pane.Show()
        self.contool.frame.auimgr.Update()

    def refresh_viewers(self,engname=None,oname=None):
        """
        Refresh open viewers.
        If engname is given all viewers for that engine will be refreshed.
        If engname and oname are given only that viewer (if it exists) will
        be refreshed.
        """
        if engname is None:
            engs  = self.open_viewers.keys()
            for eng in engs:
                eng_viewers = self.open_viewers[eng]
                for viewer in eng_viewers.values():
                    viewer.Refresh()
            return

        eng_viewers = self.open_viewers.get(engname,{})
        if oname is None:
            for viewer in eng_viewers.values():
                viewer.RefreshView()
            return

        viewer = eng_viewers.get(oname,None)
        if viewer is not None:
            viewer.RefreshView()

    #---Message handlers--------------------------------------------------------
    def msg_eng_connect(self,msg):
        """
        When an engine is started add the view() command
        """
        log.debug('Adding view() command to new engine')
        engname, = msg.get_data()
        eng = self.contool.get_engine_console(engname)
        eng.add_builtin(view, 'view')

    def msg_eng_disconnect(self,msg):
        """
        Engine disconnect message handler.
        Update viewers
        """
        engname,error = msg.get_data()
        self.refresh_viewers(engname, oname=None)

    def msg_eng_change(self,msg):
        """
        Message handler for ENGINE_STATE_CHANGE/DONE messages.
        Update viewers
        """
        engname = msg.get_from()
        self.refresh_viewers(engname, oname=None)

    def msg_open_view(self,msg):
        """
        Message handler for Views.OpenView.
        Open a GUI view for the object.
        """
        engname,oname = msg.get_data()
        self.open_viewer_pane(engname,oname)
    
    def msg_has_view(self,msg):
        """
        Message handler for Views.HasView.
        Checks if a view exists for the object type
        """
        type_string, = msg.get_data()
        return self.has_type_view(type_string)

    #---event handlers----------------------------------------------------------
    def on_viewer_close(self,event):
        """ Unsubscribe to clean up after ourselves"""
        oname = event.Window.oname
        engname = event.Window.engname
        eng_viewers = self.open_viewers.get(engname,{})
        if eng_viewers is {}:
            return
        eng_viewers.pop( oname , None)


#-------------------------------------------------------------------------------
#Uses the engine message PI_INSPECT defined in inspector tool
def view(objname):
    """
    Open a GUI view of the object: objname should be a string!
    """
    import __main__
    #check name
    try:
        o = eval(objname,__main__._engine._userdict)
    except:
        raise NameError('Object name not found')
    #send engine message
    data = (__main__._engine.name, objname)
    __main__._engine.send_msg('Views', 'OpenView', data)    
