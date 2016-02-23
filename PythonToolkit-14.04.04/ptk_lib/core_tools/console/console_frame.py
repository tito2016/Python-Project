"""
This contains the main console window:

ConsoleFrame - The main matlab style window. It uses the aui docking libary and
contains a notebook to which console pages can be added.

ConsolePage - Panel base class for console pages.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import os.path
import wx
import wx.aui as aui

from ptk_lib import VERSION
from ptk_lib.controls import aui_addons,toolpanel
from ptk_lib.resources import common16
from ptk_lib.misc import open_help
from ptk_lib.engine import eng_messages

from ptk_lib.core_tools.fileio import FileDrop, DoFileDialog
from ptk_lib.core_tools.taskicon import PTKInfoDialog

import console_icons
import console_messages

from console_dialogs import EngineChoiceDialog, RunExternalDialog, RunNewEngineDialog

#--- Ids -----------------------------------------------------------------------
ID_CUT = wx.NewId()
ID_COPY = wx.NewId()
ID_PASTE = wx.NewId()
ID_STOP = wx.NewId()
ID_PREFERENCES = wx.NewId()
ID_NEWENG = wx.NewId()
ID_RUN = wx.NewId()

ID_RUNMENU_CUR = wx.NewId()
ID_RUNMENU_NEW = wx.NewId()
ID_RUNMENU_EXT = wx.NewId()

ID_IMPORT = wx.NewId()

#-------------------------------------------------------------------------------
# Base class for all pages in the console frame notebook
#-------------------------------------------------------------------------------
class ConsolePage():
    def __init__(self):
        """
        Base class for console pages
        """
        #flag indicating whether this is an interactive console
        self.is_interactive = False

    def LoadOptions(self):
        """
        Load and apply any options relevant to the console
        """
        pass

    def OnPageStop(self):
        """
        Called to stop/keyboard interupt this console page
        """
        pass

    def OnPageClear(self):
        """
        Called to clear this console page
        """
        pass

    def OnPageSelect(self, event):
        """
        Called when this console page is selected
        """
        pass

    def OnPageClose(self, event):
        """
        Called when the console page is about to be closed. 
        """
        pass

    def GetPageMenu(self):
        """
        Returns a new Settings menu object for this console.
        This should be destroyed when finished with.
        """
        return wx.Menu()

#-------------------------------------------------------------------------------
# Frame class
#-------------------------------------------------------------------------------
class ConsoleFrame(aui_addons.AUIFrame):
    def __init__(self, tool):

        #reference to parent tool
        self.tool = tool

        #create the frame
        aui_addons.AUIFrame.__init__( self, None, -1, "PTK Console", 
                                    size=(800, 600), pos=(-1,-1) )

        #set the window icon
        ib = wx.IconBundle()
        ib.AddIcon(console_icons.console16.GetIcon())
        ib.AddIcon(console_icons.console32.GetIcon())
        ib.AddIcon(console_icons.console48.GetIcon())
        self.SetIcons(ib)

        #create the status bar
        self.CreateStatusBar()
        self.SetStatusText("Python toolkit v"+VERSION)

        #create a droptarget
        self.dt = FileDrop()
        self.SetDropTarget(self.dt)

        #create the menu
        log.debug('Creating menu')

        self.menubar = ConsoleMenu(self, self.tool)
        self.SetMenuBar(self.menubar)
        self.SetToolbarsMenu(self.menubar.toolbars_menu)
        
        #create the console pane
        log.debug('Creating ConsoleBook')
        style = aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_BOTTOM
        self.book = aui.AuiNotebook(self,-1,style=style)
        self.book.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE,self.OnPageClose)
        self.book.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED,self.OnPageChange)
        try:
            self.book.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN,self.OnTabRight)
        except:
            #wxPython 2.9.x has different event name
            self.book.Bind(aui.EVT__AUINOTEBOOK_TAB_RIGHT_DOWN,self.OnTabRight)

        pane = aui.AuiPaneInfo()
        name='Console'
        pane.Name(name) #id name
        pane.CenterPane()
    
        #pane = aui.AuiPaneInfo()
        #name='Console'
        #pane.Name(name) #id name
        #pane.Caption(name) # caption
        #pane.Center() #position
        #pane.CloseButton(False) #close button
        #pane.MaximizeButton()
        #pane.MinimizeButton()
        #pane.Floatable(False)
        #pane.Movable(True)
        #pane.BestSize( (400,600) )
        #pane.DestroyOnClose(False)
        self.auimgr.AddPane(self.book, pane)

        #add toolbars
        self._init_toolbars()

        #load the frame settings adding layout checkitems to the view menu
        self.SetSavePath('Console')
        self.SetLayoutsMenu(self.menubar.view_menu)

        #bind close events
        self.Bind(wx.EVT_CLOSE,self.OnClose)

        #update aui manager
        self.auimgr.Update()

        #subscribe to engine messages
        self.tool.msg_node.subscribe(eng_messages.ENGINE_STATE_BUSY, self.msg_eng_busy)
        self.tool.msg_node.subscribe(eng_messages.ENGINE_STATE_DONE, self.msg_eng_done)

        self.tool.msg_node.subscribe(eng_messages.ENGINE_DEBUG_PAUSED, self.msg_debug_paused)
        self.tool.msg_node.subscribe(eng_messages.ENGINE_DEBUG_RESUMED, self.msg_debug_resumed)
    
    def _init_toolbars(self):
        ##create the main toolbar
        log.debug('Creating the toolbar')
        self.maintools = MainTools(self, self.tool)
        pane = (aui.AuiPaneInfo().Name('Main toolbar')
                    .Caption('Main toolbar').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(0).LeftDockable(False)
                    .RightDockable(True))
        self.AddToolbar(self.maintools,'Main toolbar',pane,
                        helpstring = 'Show/hide the Main toolbar')

    #---interface methods-------------------------------------------------------
    def GetMenu(self,menu):
        """
        Return a reference to the menu/menubar:
        menu = 'menubar','file','edit','view','toolbars','tools','help'
        """
        menu = menu.lower()
        if menu=='menubar':
            return self.menubar
        if menu=='file':
            return self.menubar.file_menu  #file menu
        if menu=='edit':
            return self.menubar.edit_menu  #edit menu
        if menu=='view':
            return self.menubar.view_menu  #view menu
        if menu=='toolbars':
            return self.menubar.toolbars_menu  #toolbar submenu
        if menu=='tools':
            return self.menubar.tool_menu  #tool menu
        if menu=='help':
            return self.menubar.help_menu  #help menu
            
    def AddConsole(self, console, caption, bitmap=wx.NullBitmap):
        """
        Add a console as a page to the console book.
        """
        if isinstance(console, ConsolePage) is False:
            raise Exception('Page should be a subclass of ConsolePage')
        try:
            return self.book.AddPage(console, caption, False, bitmap)
        except:
            #wxPython 2.9.x aui notebook now uses image list this will break compatability for 2.8 releases so for now do not use bitmaps
            log.info('wxPython 2.9.x using bitmap=-1')
            return self.book.AddPage(console, caption, False, -1)

    def SetCurrentConsole(self, console):
        """
        Set the current console to the console given
        """
        n = self.book.GetPageIndex(console)
        if n!=-1:
            self.book.SetSelection(n)
            return True
        return False

    def GetCurrentConsole(self):
        """
        Get the current active console page
        """
        num  = self.book.GetSelection()
        if num==-1:
            page = None
        else:
            page = self.book.GetPage(num)
        return page

    def GetConsoles(self, page_type):
        """
        Get all the console pages of a particular type
        """
        npages = self.book.GetPageCount()
        res = []
        for n in range(0,npages):
            page = self.book.GetPage(n)
            if isinstance(page, page_type):
                res.append(page)
        return res

    #---message handlers ------------------------------------------------------
    def msg_eng_busy(self, msg):
        engname = msg.get_from()
        cur_console = self.tool.get_current_engine()

        #no engines or the current console is not an engine
        if cur_console is None:
            return

        #check if the current engine sent the message
        if engname == cur_console.engine:
            self.StatusBar.SetStatusText('Busy...')
            self.StatusBar.Update()

    def msg_eng_done(self, msg):
        engname = msg.get_from()
        cur_console = self.tool.get_current_engine()

        #no engines or the current console is not an engine
        if cur_console is None:
            return

        #check if the current engine sent the message
        if engname == cur_console.engine:
            self.StatusBar.SetStatusText('Done.')
            self.StatusBar.Update()

    def msg_debug_paused(self, msg):
        engname = msg.get_from()
        cur_console = self.tool.get_current_engine()

        #no engines or the current console is not an engine
        if cur_console is None:
            return

        #check if the current engine sent the message
        if engname == cur_console.engine:
            self.StatusBar.SetStatusText('Paused')
            self.StatusBar.Update()

    def msg_debug_resumed(self, msg):
        engname = msg.get_from()
        cur_console = self.tool.get_current_engine()

        #no engines or the current console is not an engine
        if cur_console is None:
            return

        #check if the current engine sent the message
        if engname == cur_console.engine:
            self.StatusBar.SetStatusText('Busy (debugging)...')
            self.StatusBar.Update()

    #---Event handlers----------------------------------------------------------
    def OnClose(self,event):
        """
        Window close event handler
        """
        self.Hide()

    def OnPageClose(self, event):
        """
        Call the page.OnClose() method to check whether to proceed
        """
        num  = self.book.GetSelection()        
        if num!=-1:
            page = self.book.GetPage(num)
            page.OnPageClose(event)
        
        #check if there are no more open pages and published the console changed
        #message as the PageChange event does not happen.
        npages = self.book.GetPageCount()
        #if the event has not been skipped, it will be closed
        if (npages ==1) and event.GetSkipped():
            #so publish the console changed message
            self.tool.msg_node.publish_msg( console_messages.CONSOLE_SWITCHED)


    def OnPageChange(self, event):

        #get the new selection
        num  = self.book.GetSelection()  
        if num==-1:
            page = None
            is_engine = False
        else:
            page = self.book.GetPage(num)
            page.OnPageSelect(event)
            is_engine = page.is_interactive
        event.Skip()
        
        #update the status bar
        if is_engine is True:
            busy, debug, profile = page.get_state() 
            if busy and debug:
                string = 'Busy (debugging)...'
            elif busy and profile:
                string = 'Busy (profiling)...'
            elif busy:
                string = 'Busy...'
            else:
                string = 'Ready' 
        else:
            string = ''
        self.StatusBar.SetStatusText(string)
        self.StatusBar.Update()

        #publish the console changed message
        self.tool.msg_node.publish_msg( console_messages.CONSOLE_SWITCHED)

    def OnTabRight(self, event):
        #Open the control menu for the current console tab
        #num = self.book.GetSelection()
        #if num==-1:
        #    return
        #conpage = self.book.GetPage(num)

        #use the console tab that was click on...
        tab = event.GetEventObject()
        num = tab.GetActivePage()
        conpage = tab.GetWindowFromIdx(num)

        menu = conpage.GetPageMenu()
        self.PopupMenu(menu)
        menu.Destroy() 
        

#-------------------------------------------------------------------------------
# Frame menu class
#-------------------------------------------------------------------------------
class ConsoleMenu(wx.MenuBar):
    def __init__(self,parent, tool):
        wx.MenuBar.__init__(self)
        
        #parent tool
        self.tool = tool

        #parent frame
        self.parent = parent
        
        self.file_menu       = wx.Menu()     #file menu
        self.edit_menu       = wx.Menu()     #edit menu
        self.view_menu       = wx.Menu()     #view menu
        self.toolbars_menu   = wx.Menu()     #toolbar submenu
        self.tool_menu       = wx.Menu()     #tool menu
        self.help_menu       = wx.Menu()     #help menu

        ##add the menus to the menu bar
        self.Append(self.file_menu, "&File")
        self.Append(self.edit_menu, "&Edit")
        self.Append(self.view_menu, "&View")
        self.Append(self.tool_menu, "&Tools")
        self.Append(self.help_menu, "&Help")

        ##file menu
        self.file_menu.Append(wx.ID_NEW ,'&New\tCtrl+N','Create a new file in the editor')
        self.file_menu.Append(wx.ID_OPEN,'&Open\tCtrl+O','Open an existing file in the editor')
        self.file_menu.AppendSeparator()
        self.file_menu.Append(ID_IMPORT,'&Import...','Import python data from file')
        self.file_menu.AppendSeparator()
        self.file_menu.Append(wx.ID_CLOSE, '&Hide Console\tCtrl+H','Hides the console window to the taskbar')
        self.file_menu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q','Exit PTK')
        
        #bindings
        self.parent.Bind(wx.EVT_MENU, self.OnNew, id=wx.ID_NEW)
        self.parent.Bind(wx.EVT_MENU, self.OnOpen, id=wx.ID_OPEN)
        self.parent.Bind(wx.EVT_MENU, self.OnImport, id=ID_IMPORT)
        self.parent.Bind(wx.EVT_MENU, self.OnClose, id=wx.ID_CLOSE)
        self.parent.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
               
        ##edit menu
        self.edit_menu.Append(ID_CUT,'Cu&t\tCtrl+X','Cut selection to clipboard')
        self.edit_menu.Append(ID_COPY,'&Copy\tCtrl+C','Copy selection to clipboard')
        self.edit_menu.Append(ID_PASTE,'&Paste\tCtrl+V','Paste from clipboard')
        self.edit_menu.AppendSeparator()
        self.edit_menu.Append(ID_PREFERENCES, 'Preferences', 'Edit the program preferences') 
        
        #bindings
        self.parent.Bind(wx.EVT_MENU, self.OnCut, id=ID_CUT)
        self.parent.Bind(wx.EVT_MENU, self.OnCopy, id=ID_COPY)
        self.parent.Bind(wx.EVT_MENU, self.OnPaste, id=ID_PASTE)
        self.parent.Bind(wx.EVT_MENU, self.OnPreferences, id=ID_PREFERENCES)
        self.parent.Bind(wx.EVT_UPDATE_UI, self.OnUpdateImport, id=ID_IMPORT)
        
        ##view menu
        self.view_menu.AppendSubMenu(self.toolbars_menu , 'Toolbars...','Show Toolbars')
        self.view_menu.AppendSeparator()
        #layouts added in auimixin

        ##tools menu       
        #tools add themselves here

        ##Help menu
        self.help_menu.Append(wx.ID_HELP, '&Help', 'Open the python documentation...') 
        tipid=wx.NewId()
        self.help_menu.Append(tipid, '&Show tips', 'Show tips') 
        self.help_menu.Append(wx.ID_ABOUT, '&About...', 'About this program...') 

        #bindings
        self.parent.Bind(wx.EVT_MENU, self.OnHelp, id=wx.ID_HELP)
        self.parent.Bind(wx.EVT_MENU, self.OnTip, id=tipid)
        self.parent.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        
    #---Event handlers---------------------------------------------------------- 
    def OnUpdateImport(self, event):
        #enable/disable import menu item.
        eng = self.tool.get_current_engine()
        if eng is None:
            self.file_menu.Enable(ID_IMPORT, False)
        else:
            self.file_menu.Enable(ID_IMPORT, True)
        
    #file menu
    def OnNew(self,event):
        """New file (menu and toolbar) handler"""
        self.tool.msg_node.send_msg('Editor','New',())

    def OnOpen(self,event):
        """Open file handler"""
        #Create the file open dialog.
        filepaths,index = DoFileDialog(self.parent, wildcard = "Python source (*.py,*.pyw)|*.py;*.pyw|All files (*,*.*)|*.*;*")
        if filepaths==None:
            return
        self.tool.msg_node.send_msg('Editor','Open',filepaths)

    def OnImport(self,event):
        """Import python data  from file"""
        self.tool.msg_node.send_msg('FileIO','Import',('',))

    def OnClose(self,event):
        self.parent.Hide()

    def OnExit(self, event):
        """Called when exit menu item selected"""
        app = wx.GetApp()
        app.Exit()

    #edit menu
    def OnCut(self,event):
        """Calls the cut method of the active pane (if it exists)"""
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Cut()
            except AttributeError:
                pass

    def OnCopy(self,event):
        """Menu handler: Calls the copy method of the active pane (if it exists)"""
        event.Skip()
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Copy()
            except AttributeError:
                pass
         
                
    def OnPaste(self,event):
        """Calls the paste method of the active pane (if it exists)"""
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Paste()
            except AttributeError:
                pass

    def OnPreferences(self,event):
        """Show the settings dialog"""
        self.tool.msg_node.send_msg('TaskIcon','Settings.Show',())

    #view menu
    #
    # done in auimixin
    #

    #tools menu
    #
    # added by tools
    #

    #help menu
    def OnHelp(self,event):
        """Open the help browser"""
        open_help()  

    def OnTip(self,event):
        """Open the help tips"""
        app=wx.GetApp()
        app.ShowTips(override=True)

    def OnAbout(self,event):
        """Opens the about box"""
        PTKInfoDialog()



#-------------------------------------------------------------------------------
# Toolbar class
#-------------------------------------------------------------------------------
class MainTools(toolpanel.ToolPanel):
    def __init__(self, parent, tool):

        toolpanel.ToolPanel.__init__(self, parent, -1)
        self.SetStatusBar(parent.StatusBar)

        self.tool = tool

        #set the icon size
        self.SetToolBitmapSize((16,16))
        
        #load some icons
        new_bmp     = common16.document_new.GetBitmap()
        open_bmp    = common16.document_open.GetBitmap()
        cut_bmp     = common16.edit_cut.GetBitmap()
        copy_bmp    = common16.edit_copy.GetBitmap()
        paste_bmp   = common16.edit_paste.GetBitmap()
        clear_bmp   = common16.edit_clear.GetBitmap() 
        stop_bmp    = console_icons.engine_stop.GetBitmap()
        help_bmp    = common16.help_browser.GetBitmap()

        engnew_bmp   = console_icons.engine_new.GetBitmap()

        run_bmp         = console_icons.run.GetBitmap()
        run_neweng_bmp  = console_icons.run_neweng.GetBitmap()
        run_ext_bmp     = console_icons.run_ext.GetBitmap()

        settings_bmp = console_icons.console_settings.GetBitmap()

        #new
        self.AddTool( wx.ID_NEW, new_bmp, wx.ITEM_NORMAL, 
                      'New file','Create a new file in the editor')
        self.Bind(wx.EVT_TOOL, self.OnNew, id=wx.ID_NEW)

        #open
        self.AddTool( wx.ID_OPEN, open_bmp, toolpanel.ITEM_DROPDOWN,
                        'Open / Open Recent','Open an existing file in the editor')
        self.Bind(wx.EVT_TOOL, self.OnOpen, id=wx.ID_OPEN)

        self.AddSeparator()

        #new engine
        self.AddTool( ID_NEWENG, engnew_bmp, wx.ITEM_NORMAL, 
                      'New Engine','Create a new interactive engine')
        self.Bind(wx.EVT_TOOL, self.OnNewEngine, id=ID_NEWENG)

        #Run
        self.AddTool( ID_RUN, run_bmp, toolpanel.ITEM_DROPDOWN, 
                      'Run script in current engine/Other run options',
            'Run a Python script in the current engine/Show other run options')
        self.Bind(wx.EVT_TOOL, self.OnRun, id=ID_RUN)

        self.AddSeparator()

        #Stop
        self.AddTool( wx.ID_STOP, stop_bmp, wx.ITEM_NORMAL,
                    'Stop running command',
                    'Stop the active console via a keyboard interupt [Ctrl+C]')
        self.Bind(wx.EVT_TOOL, self.OnStop, id=wx.ID_STOP)

        self.AddSeparator()

        #-----------------------------------------------------------------------
        
        #cut
        self.AddTool( wx.ID_CUT, cut_bmp, wx.ITEM_NORMAL, 'Cut', 
                      longHelp='Cut selection to the clipboard')
        self.Bind(wx.EVT_TOOL, self.OnCut, id=wx.ID_CUT)
        
        #copy
        self.AddTool( wx.ID_COPY, copy_bmp, wx.ITEM_NORMAL, 'Copy',
                      longHelp='Copy selection to the clipboard')
        self.Bind(wx.EVT_TOOL, self.OnCopy, id=wx.ID_COPY)
        
        #paste
        self.AddTool( wx.ID_PASTE, paste_bmp, wx.ITEM_NORMAL, 'Paste',
                     longHelp='Paste from clipboard')
        self.Bind(wx.EVT_TOOL, self.OnPaste, id=wx.ID_PASTE)
        
        #Clear console
        self.AddTool( wx.ID_CLEAR, clear_bmp, wx.ITEM_NORMAL,
                        'Clear console',
                        longHelp='Clear the current console')
        self.Bind(wx.EVT_TOOL, self.OnClear, id=wx.ID_CLEAR)

        self.AddSeparator()
        #-----------------------------------------------------------------------
        
        #help
        self.AddTool( wx.ID_HELP, help_bmp, wx.ITEM_NORMAL, 'Help',
                      longHelp='Open help documentation')
        self.Bind(wx.EVT_TOOL, self.OnHelp, id=wx.ID_HELP)
        #-----------------------------------------------------------------------
        self.Realize()


        #----------------------
        #create the run menu
        #----------------------
        self.run_menu = wx.Menu()
        self.Bind( wx.EVT_UPDATE_UI, self.OnRunMenuUI)

        run_cureng_item = wx.MenuItem( self.run_menu, ID_RUNMENU_CUR ,
                            'Run script in current engine', 
                            'Run script in current engine', wx.ITEM_NORMAL)
        run_cureng_item.SetBitmap(run_bmp)
        self.run_menu.AppendItem(run_cureng_item)
        self.run_menu.Bind(wx.EVT_MENU, self.OnRunCurEng, run_cureng_item)

        run_neweng_item = wx.MenuItem( self.run_menu, ID_RUNMENU_NEW,
                            'Run script in a new engine', 
                            'Run script in a new engine', wx.ITEM_NORMAL)
        run_neweng_item.SetBitmap(run_neweng_bmp)
        self.run_menu.AppendItem(run_neweng_item)
        self.run_menu.Bind(wx.EVT_MENU, self.OnRunNewEng, run_neweng_item)

        run_ext_item = wx.MenuItem( self.run_menu, ID_RUNMENU_EXT,
                            'Run script as an external process', 
                            'Run script as an external process', wx.ITEM_NORMAL)
        run_ext_item.SetBitmap(run_ext_bmp)
        self.run_menu.AppendItem(run_ext_item)
        self.run_menu.Bind(wx.EVT_MENU, self.OnRunExt, run_ext_item)

    #---Event handlers----------------------------------------------------------
    def OnNew(self,event):
        """New file (menu and toolbar) handler"""
        self.tool.msg_node.send_msg('Editor','New',())

    def OnOpen(self,event):
        """Open file (menu and toolbar) handler"""
        if event.IsChecked():
            #Show dropdown menu
            but = event.GetEventObject()
    
            #create a menu and add recent editor files
            menu = wx.Menu()
            app = wx.GetApp()
            editor = app.toolmgr.get_tool('Editor')
            editor.frame.filehistory.AddFilesToThisMenu(menu)
            menu.Bind(wx.EVT_MENU_RANGE, self.OnMenuOpen, id=wx.ID_FILE1, 
                        id2=wx.ID_FILE9)
            but.PopupMenu(menu)

            # make sure the button is "un-stuck"
            menu.Destroy()
        else:
            #Create the file open dialog.
            filepaths,index = DoFileDialog(self.Parent, wildcard = "Python source (*.py,*.pyw)|*.py;*.pyw|All files (*,*.*)|*.*;*")
            if filepaths==None:
                return
            self.tool.msg_node.send_msg('Editor','Open',filepaths)
        self.Refresh()
    
    def OnMenuOpen(self, event):
        """Handler for recent files menu"""
        filenum = event.GetId() - wx.ID_FILE1
        app = wx.GetApp()
        editor = app.toolmgr.get_tool('Editor')
        path = editor.frame.filehistory.GetHistoryFile(filenum)
        editor.frame.OpenFile(path)

    def OnNewEngine(self,event):
        """
        Create a new engine
        """
        #show a dialog here to create a new engine and console.
        d = EngineChoiceDialog(self.Parent, 'Start a new engine')
        res=d.ShowModal()
        if res==wx.ID_OK:
            englabel,engtype = d.GetValue()
            self.tool.start_engine(engtype, englabel)
        d.Destroy()
        self.Refresh()

    def OnRun(self, event):
        """
        Run script /show run menu
        """
        if event.IsChecked():
            #show drop down run menu
            but = event.GetEventObject()
            but.PopupMenu(self.run_menu)

        else:
            #run in current engine
            eng = self.tool.get_current_engine()
            if eng is None:
                self.OnRunNewEng(event)
            else:
                self.OnRunCurEng(event)

    def OnRunMenuUI(self, event):
        id = event.Id
        if id == ID_RUNMENU_CUR:
            eng = self.tool.get_current_engine()
            if eng is None:
                event.Enable(False)
            else:
                event.Enable(True)

    def OnRunCurEng(self, event):
        #Run in current engine
        paths, index = DoFileDialog(self, message="Choose a file",
            defaultFile="",
            wildcard='Python scripts|*.py;*.pyw|All files|*.*;*',
            style=wx.OPEN | wx.CHANGE_DIR,
            engname = None)
            
        if paths is None:
            return

        self.tool.exec_file( paths[0])

    def OnRunNewEng(self, event):
        #Run in new engine
        d = RunNewEngineDialog(self.Parent)
        res=d.ShowModal()
        if res==wx.ID_OK:
            filepath,engtype = d.GetValue()
            label = os.path.basename(filepath)
            self.tool.start_engine( engtype, label , filepath )
        d.Destroy()
        
    def OnRunExt(self, event):
        #show the d dialog here to launch a new script.
        d = RunExternalDialog(self.Parent, 'Run script as external process')
        res = d.ShowModal()
        if res==wx.ID_OK:
            filepath,args = d.GetValue()
            self.tool.run_script( filepath, args)
        d.Destroy()

    def OnCut(self,event):
        """Calls the cut method of the active pane (if it exists)"""
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Cut()
            except AttributeError:
                pass

    def OnCopy(self,event):
        """Calls the copy method of the active pane (if it exists)"""
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Copy()
            except AttributeError:
                pass

    def OnPaste(self,event):
        """Calls the paste method of the active pane (if it exists)"""
        active= self.FindFocus()
        if active is not None: 
            try:
                active.Paste()
            except AttributeError:
                pass

    def OnClear(self,event): 
        console = self.Parent.GetCurrentConsole()
        if console is None:
            return
        console.OnPageClear()
    
    def OnStop(self,event):
        console = self.Parent.GetCurrentConsole()
        if console is None:
            return
        console.OnPageStop()

    def OnHelp(self,event):
        """Open the help browser"""
        open_help()
    
