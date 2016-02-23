"""
Editor tool.

A simple python code editor and integrated debugger with just enough features.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui

from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus import mb_protocol
from ptk_lib.tool_manager import Tool
from ptk_lib.engine import eng_messages, eng_misc

#other tool imports
from ptk_lib.core_tools.fileio import Importer, DoFileDialog
from ptk_lib.core_tools.console import console_messages

#editor imports
from editor_frame import EditorFrame
import editor_messages
import editor_icons

#debugger imports
from dbg_controls import DebugConsoleTools, BreakPointListPanel

#---the tools class-------------------------------------------------------------
class Editor(Tool):
    name = 'Editor'
    descrip = 'Core tool providing a simple python code editor and integrated debugger with just enough features'
    author = 'T.Charrett'
    requires = ['TaskIcon','Console','FileIO']           
    core = True            
    icon = editor_icons.editor32

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('Editor')
        self.msg_node.connect(self.msg_bus)

        #-----------------------------------------------------------------------
        #subscribe to application messages
        #       - this is done first to ensure the debugger interace is always
        #       updated before other subscribers are processed (the toolbars in
        #       this tool then any other tools loaded after the editor).
        #-----------------------------------------------------------------------
        self.msg_node.subscribe('App.Init',self.msg_app_init)
        self.msg_node.subscribe('App.ExitCheck',self.msg_app_exitcheck)
        self.msg_node.subscribe('App.Exit',self.msg_app_exit)

        #Add the edit command and debugger breakpoints when a new engine starts.
        self.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                self.msg_engine_connect)  

        self.msg_node.subscribe(    console_messages.CONSOLE_SWITCHED,
                                    self.msg_console_switched)
                                    
        #on debug messages - update the editor breakpoint and paused markers
        self.msg_node.subscribe(    eng_messages.ENGINE_STATE_DONE, 
                                    self.msg_eng_done)
                                                                        
        self.msg_node.subscribe(    eng_messages.ENGINE_DEBUG_TOGGLED,
                                    self.msg_debug_toggled)

        self.msg_node.subscribe(    eng_messages.ENGINE_DEBUG_PAUSED, 
                                    self.msg_debug_paused)
                                    
        self.msg_node.subscribe(    eng_messages.ENGINE_DEBUG_RESUMED, 
                                    self.msg_debug_resumed)


        #-----------------------------------------------------------------------
        #Register message handlers
        #-----------------------------------------------------------------------
        self.msg_node.set_handler(editor_messages.EDITOR_NEW,   
                                    self.msg_new)  #open the a new file
        self.msg_node.set_handler(editor_messages.EDITOR_OPEN,  
                                    self.msg_open) #open the file(s)
        self.msg_node.set_handler(editor_messages.EDITOR_SHOW,  
                                    self.msg_show) #show the editor
        self.msg_node.set_handler(editor_messages.EDITOR_HIDE,  
                                    self.msg_hide) #hide the editor

        #-----------------------------------------------------------------------
        # Internals
        #-----------------------------------------------------------------------
        #break points (set in all engines)
        self.bpoints = eng_misc.DictList()
        self.bp_counter = 0

        #-----------------------------------------------------------------------
        # GUI components
        #-----------------------------------------------------------------------
        #create the editor frame
        self.frame =  EditorFrame(self)
        self.notebook = self.frame.notebook

        #Add taskbar menu item
        taskicon = self.toolmgr.get_tool('TaskIcon')
        bmp = editor_icons.editor16.GetBitmap()
        taskicon.add_menu_item(wx.NewId(), 'Open the Editor',
                   'Open the Editor window', self.on_show, bmp)

        #Add menu item to console window
        console = self.toolmgr.get_tool('Console')
        bmp = editor_icons.editor16.GetBitmap()
        console.add_menu_item('tools', wx.NewId(), 'Editor',
                    'Open the Editor window', self.on_show, bmp)

        #Add the debugger breakpoints pane to the console
        ctrl = BreakPointListPanel(console.frame, self)
        pane = aui.AuiPaneInfo()
        name='Debugger Breakpoints'
        pane.Name(name) #id name
        pane.Caption('Debugger Breakpoints')
        pane.CloseButton(True) #close button
        pane.MaximizeButton(True)
        pane.DestroyOnClose(False)
        pane.Floatable(True)
        pane.Resizable(True)
        pane.MinSize( (100,200))
        pane.MaxSize( (-1,-1))
        pane.Right()
        pane.Dock()
        pane.Hide()

        console.frame.auimgr.AddPane(ctrl, pane) #add the pane
        self.console_pane=console.frame.auimgr.GetPane(name) #store a reference

        #Add a menu item to show/hide the debugger pane
        


        #Add a debugger toolbar to the console frame
        self.debugtools = DebugConsoleTools(console.frame, self)
        pane = (aui.AuiPaneInfo().Name('Debuger toolbar')
                    .Caption('Debuger toolbar').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(1).Position(1)
                    .LeftDockable(False).RightDockable(False))
        console.frame.AddToolbar(self.debugtools,'Debuger toolbar',pane,
                        helpstring = 'Show/hide the Debugger toolbar') 

        #-----------------------------------------------------------------------
        #register file importer
        #-----------------------------------------------------------------------
        fileio = self.toolmgr.get_tool('FileIO')
        self.importer = EditorImporter(self.frame)
        fileio.register_importer( self.importer )

        log.info('Done Initialising tool')

    #---Frame Interfaces--------------------------------------------------------
    def show_editor(self):
        """
        Show the Editor frame
        """
        self.frame.Show()
        self.frame.Raise()

    def hide_editor(self):
        """
        Hide the Editor frame
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
    
    def edit_file(self, file, lineno=0):
        """
        Open the file in the editor and scroll to the line given
        """
        self.frame.notebook.OpenFile(file)
        #TODO: scroll to line
        self.frame.Show()
        self.frame.Raise()

    #---debugger interfaces-----------------------------------------------------
    def set_breakpoint(self, filename,lineno,
                        condition=None,ignore_count=None,trigger_count=None):
        """
        Set a breakpoint for all engines.
        Returns the new breakpoint id (used to edit/clear breakpoints).
        """
        #create new id.
        id = self.bp_counter
        self.bp_counter+=1 

        #store in DictList
        bpdata = {  'id':id,'filename':filename, 'lineno':lineno,
                    'condition':condition, 'ignore_count':ignore_count,
                    'trigger_count':trigger_count }
        self.bpoints.append(bpdata)
        
        #set the breakpoint in each engine.
        console = self.app.toolmgr.get_tool('Console')
        engines = console.get_all_engines(active=True)
        for eng in engines:
            eng.debugger.set_breakpoint(bpdata)

        #add a breakpoint marker to the editor page
        page = self.frame.notebook.GetPageFromPath(filename)
        if page is not None:
            page.AddBreakpointMarker( id, lineno )

        #publish a breakpoint set message
        self.msg_node.publish_msg(  editor_messages.EDITOR_BREAKPOINT_SET,
                                    (bpdata,)  )        
        return id        

    def clear_breakpoint(self, id):
        """
        Clear the debugger breakpoint with the id given for all engines.
        """
        bps = self.bpoints.filter( ('id',),(id,) )
        if len(bps)==0:
            raise Exception('No breakpoint with id '+str(id))
        bpdict = bps[0]

        #clear the breakpoint in each engine
        console = self.app.toolmgr.get_tool('Console')
        engines = console.get_all_engines(active=True)
        for eng in engines:
            eng.debugger.clear_breakpoint(id)
        
        #remove from internal breakpoint list
        self.bpoints.remove(bpdict)

        #clear any markers from the editor pages
        page = self.frame.notebook.GetPageFromPath( bpdict['filename'] )
        if page is not None:
            page.DeleteBreakpointMarker( id )

        #publish a breakpoint cleared message
        self.msg_node.publish_msg(  editor_messages.EDITOR_BREAKPOINT_CLEARED,
                                    (id,)  )        

    def clear_breakpoints(self, filename, lineno=None):
        """
        Clear the debugger breakpoints in the filename given. If the optional 
        lineno is given clear breakpoints at this line in the file given.
        """        
        #get breakpoints
        bps = self.get_breakpoints(filename, lineno)

        #no breakpoints found?
        if bps==[]:
            return
            
        bpids = []
        for bp in bps:
            bpids.append(bp['id'])
            
        #clear the breakpoint in each engine
        console = self.app.toolmgr.get_tool('Console')
        engines = console.get_all_engines(active=True)
        for eng in engines:
            eng.debugger.clear_breakpoints(bpids)
           
        #remove from the internal breakpoint list and clear any markers in the
        #editor pages
        page = self.frame.notebook.GetPageFromPath( filename )
        for bp in bps:
            self.bpoints.remove(bp)
            if page is not None:
                page.DeleteBreakpointMarker( bp['id'] )

        #published a breakpoint cleared message
        self.msg_node.publish_msg(  editor_messages.EDITOR_BREAKPOINT_CLEARED,
                                    bpids )        

    def clear_all_breakpoints(self):
        """
        Clear all set breakpoints
        """
        #clear all the breakpoints in each engine
        console = self.app.toolmgr.get_tool('Console')
        engines = console.get_all_engines()

        for eng in engines:
            res = self.msg_node.send_msg( eng.engine, 
                                    eng_messages.ENG_DEBUG_CLEARBP,
                                    (None,), True )

        #clear the internal brealpoint list
        self.bpoints.clear()

        #clear any markers from the editor pages
        pages = self.frame.notebook.GetAllPages()
        for page in pages:
            page.DeleteAllBreakpointMarkers()

        #published a breakpoint cleared message
        self.msg_node.publish_msg(  editor_messages.EDITOR_BREAKPOINT_CLEARED,
                                    (None,)  )        

    def modify_breakpoint(self, id, **kwargs):
        """
        Modify a breakpoint.

        Note: Only modify the keywords 'condition', 'trigger_count' or 
        'ignore_count'. 'filename' and 'lineno' can also be used if the 
        file is not open in the editor (or by the editor page itself to move a 
        breakpoint).

        e.g. modify_breakpoint( id=1, filename='test.py', lineno=23) will modify
        the breakpoint filename and lineno. To pass a dictionary of changes use 
        **dict.
        """
        bps = self.bpoints.filter( ('id',),(id,) )
        if len(bps)==0:
            raise Exception('No breakpoint with id '+str(id))
        bpdict = bps[0]

        #modify the breakpoint in each engine
        console = self.app.toolmgr.get_tool('Console')
        engines = console.get_all_engines()

        for eng in engines:
            res = self.msg_node.send_msg( eng.engine, 
                                    eng_messages.ENG_DEBUG_EDITBP,
                                    (id, kwargs), True )

        #modify the breakpoint data dictionary.
        bpdict.update( kwargs )

        #modify any markers if the file is open in the editor
        page = self.frame.notebook.GetPageFromPath( bpdict['filename'] )
        if page is not None:
            page.DeleteBreakpointMarker( id )
            page.AddBreakpointMarker( id, bpdict['lineno'] )
            
        #published a breakpoint changed message
        self.msg_node.publish_msg(  editor_messages.EDITOR_BREAKPOINT_CHANGED,
                                   (id,kwargs)  )     

    def get_breakpoint(self, id):
        """
        Get the breakpoint by id
        """
        res = self.bpoints.filter( keys=('id',), values=( id,) )
        if res==[]:
            return None
        return res[0]

    def get_breakpoints(self, filename=None, lineno=None):
        """
        Get the breakpoints currently set in the filename given if None return
        all breakpoints. If lineno is given return only breakpoints at this line
        in the file given.
        """
        if filename is None:
            return self.bpoints.items()
        if lineno is None:
            return self.bpoints.filter( keys=('filename',),
                                        values=(filename,)  )
        else:
            return self.bpoints.filter( keys=('filename','lineno'), 
                                        values=(filename, lineno)   )

    def get_breakpoint_files(self):
        """
        Get a list of all files where breakpoints are set
        """
        return self.bpoints.values(key='filename')

    #---Message handlers-------------------------------------------------------
    def msg_show(self,msg):
        """
        Message handler for Editor.Show and wx.Event from menu
        """
        self.frame.Show()
        self.frame.Raise()

    def msg_hide(self,msg):
        """
        Message handler for Editor.Hide
        """
        self.frame.Hide()

    def msg_new(self,msg):
        """
        Message handler for Editor.New
        """
        self.frame.notebook.New()
        self.frame.Show()
        self.frame.Raise()

    def msg_open(self,msg):
        """
        Message handler for Editor.Open
        data=list of files to open in editor
        """
        filepaths = msg.get_data()
        if filepaths is ():
            #Create the file open dialog.
            filepaths,index = DoFileDialog(self.frame, wildcard = "Python source (*.py,*.pyw)|*.py;*.pyw|All files (*,*.*)|*.*;*")
            if filepaths==None:
                return

        if (filepaths is not None) and (filepaths!=[]):
            #open the file requested
            for path in filepaths:
                self.frame.notebook.OpenFile(path)
        self.frame.Show()
        self.frame.Raise()

    def msg_app_init(self,msg):
        """
        Listener for App.Init message
        Sent when application starts
        """
        #load the main window layouts (in aui mixin class)
        self.frame.LoadLayouts()

    def msg_app_exitcheck(self,msg):
        """
        Check its ok for the application to exit
        """
        #check for unsaved files
        res= self.frame.notebook.CheckClose()
        if res is False:
            self.app.VetoExit()

    def msg_app_exit(self,msg):
        """
        Listener for App.Exit message
        Save settings on application exit
        """
        #save the main window layouts (in aui mixin class)
        self.frame.SaveLayouts()
        #save the recent files list
        cfg = self.app.GetConfig()
        cfg.SetPath("Editor//")
        self.frame.filehistory.Save(cfg)
        cfg.Flush()

    def msg_engine_connect(self,msg):
        """
        Engine manager - Engine.Started message handler
        """
        log.debug('Adding edit() command to new engine')
        engname = msg.get_data()[0]

        #get the new engine interface
        app = wx.GetApp()
        console = app.toolmgr.get_tool('Console')
        eng = console.get_engine_console(engname)

        #When an engine is started add the edit() command
        eng.add_builtin(edit, 'edit')

        #add any set breakpoints to this engine's debugger
        for bpdata in self.bpoints:
            eng.debugger.set_breakpoint(bpdata)

    def msg_debug_toggled(self, msg):
        """
        Debugger enabled/disabled message
        """
        #update the bp markers in the editor pages
        pages = self.frame.notebook.GetAllPages()
        for page in pages:
            page.UpdateBreakpointSymbols()

    def msg_eng_done(self,msg):
        engname = msg.get_from()
        debug, profile = msg.data
        console = self.app.toolmgr.get_tool('Console')
        if console.is_engine_current(engname):
            #update any displayed paused markers
            self.frame.notebook.UpdatePauseMarkers()
    
    def msg_debug_paused(self,msg):
        engname = msg.get_from()
        paused_at, scope_list, active_scope, flags = msg.data
        console = self.app.toolmgr.get_tool('Console')
        if console.is_engine_current(engname):
            #update any displayed paused markers
            self.frame.notebook.UpdatePauseMarkers()

    def msg_debug_resumed(self,msg):
        engname = msg.get_from()
        console = self.app.toolmgr.get_tool('Console')
        if console.is_engine_current(engname):
            #update any displayed paused markers
            self.frame.notebook.UpdatePauseMarkers()

    def msg_console_switched(self, msg):
        """
        The current active console switched.
        """
        #update the paused/line number markers
        self.frame.notebook.UpdatePauseMarkers()

        #update the bp markers in the editor pages
        pages = self.frame.notebook.GetAllPages()
        for page in pages:
            page.UpdateBreakpointSymbols()

    #---other-------------------------------------------------------------------
    def on_show(self, event):
        """wx event handler for the taskbar and console menu items"""
        self.frame.Show()
        self.frame.Raise()

#-------------------------------------------------------------------------------
# Engine magic command - this is added to engines __builtin__ module.
#-------------------------------------------------------------------------------
def edit(filename):
    """
    Edit a file in the ptk editor
    """
    import os
    import __main__

    #check file exists
    filepath = os.path.abspath(filename)
    cwd = os.getcwd()
    #a full path given
    if os.path.exists(filepath) is False:
        raise Exception('File does not exist: '+filename)
    #send the editor message
    __main__._engine.send_msg('Editor','Open',(filepath,))

#-------------------------------------------------------------------------------
#FileIO importer
#-------------------------------------------------------------------------------
class EditorImporter(Importer):
    def __init__(self,frame):
        Importer.__init__( self,'Open in the Editor', ['','.py','.pyw','.txt'],
                            data=False,
                            wildcards=["Python source (*.py,*.pyw)|*.py;*.pyw;",
                                        "Text file (*.txt)|*.txt"],
                            descrip = 'Open the file in the Editor' )
        self.frame = frame

    def __call__(self,filename):
         self.frame.OpenFile(filename)


