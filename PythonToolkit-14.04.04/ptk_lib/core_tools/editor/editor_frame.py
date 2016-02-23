"""
This contains the main editor window:

EditorFrame - The main editor window.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---imports---------------------------------------------------------------------
import wx                           #for gui elements
import wx.aui as aui

from ptk_lib import VERSION
from ptk_lib.controls import aui_addons
from ptk_lib.controls import toolpanel

from ptk_lib.resources import common22
from ptk_lib.misc import open_help
from ptk_lib.core_tools.fileio import FileDrop
from ptk_lib.core_tools.taskicon import PTKInfoDialog

from ptk_lib.core_tools.console import console_icons


import editor_icons
from editor_notebook import EditorNotebook
from search_panel    import SearchPanel
from dbg_controls import DebugEditorTools, BreakPointListPanel


#ids for run menu items
ID_RUNMENU_SEL = wx.NewId()
ID_RUNMENU_CUR = wx.NewId()
ID_RUNMENU_NEW = wx.NewId()
ID_RUNMENU_EXT = wx.NewId()

#---Editor frame ---------------------------------------------------------------
class EditorFrame(aui_addons.AUIFrame):
    """Top level Editor window"""
    def __init__(self, tool):
        """Create editor window"""
        aui_addons.AUIFrame.__init__(self, None, -1, "PTK Editor",size=(800,600),pos=(-1,-1))

        #store a reference to the editor tool in the frame.
        self.tool = tool

        #set the window icons
        ib = wx.IconBundle()
        ib.AddIcon(editor_icons.editor16.GetIcon())
        ib.AddIcon(editor_icons.editor32.GetIcon())
        ib.AddIcon(editor_icons.editor48.GetIcon())
        self.SetIcons(ib)

        #create statusbar
        self.CreateStatusBar()
        self.SetStatusText("Python toolkit v"+VERSION)

        #create the menu
        self._CreateMenu()
        self.SetToolbarsMenu(self.menubar.toolbars_menu)
        self.SetPanesMenu(self.menubar.view_menu)

        #create aui panes
        self._CreateNotebook()
        self._CreateSearchPane()  
        self._CreateDebuggerPane()

        #create the main tool bar
        self._CreateTools()

        #list of recent files:
        self.filehistory = wx.FileHistory(9)
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Editor//")
        self.filehistory.Load(cfg)
        self.filehistory.UseMenu(self.menubar.recent_menu)
        self.filehistory.AddFilesToMenu()
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        #create a droptarget
        self.dt = FileDrop(self.notebook.OpenFile)
        self.SetDropTarget(self.dt) 

        #get window close events
        self.Bind( wx.EVT_CLOSE, self.OnClose)

        #load the frame settings adding layout checkitems to the view menu
        self.SetSavePath('Editor')
        self.SetLayoutsMenu(self.menubar.layouts_menu)

        #update aui manager
        self.auimgr.Update()

        log.info('Done Initialising Editor Frame')

    def _CreateMenu(self):
        self.menubar = EditorMenu(self)
        #finally create the menubar
        self.SetMenuBar(self.menubar)
 
    def _CreateTools(self):
        self.tools = EditorTools(self)
        #add this toolbar to aui manager
        pane = (aui.AuiPaneInfo().Name('Editor toolbar')
                    .Caption('Editor toolbar').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(0).LeftDockable(False)
                    .RightDockable(False))

        #add to the window using aui manager
        self.AddToolbar( self.tools, 'Editor toolbar', pane,
                         helpstring = 'Show/Hide the editor toolbar' )

        self.formattools = FormatTools(self)
        #add this toolbar to aui manager
        pane = ( aui.AuiPaneInfo().Name('Format toolbar')
                    .Caption('Format toolbar').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(0).Position(1)
                    .LeftDockable(False)
                    .RightDockable(False) )

        #add to the window using aui manager
        self.AddToolbar( self.formattools, 'Format toolbar', pane, 
                         helpstring = 'Show/Hide the Format toolbar' )

        self.dbgtools = DebugEditorTools(self, self.tool)
        #add this toolbar to aui manager
        pane = ( aui.AuiPaneInfo().Name('Debugger toolbar')
                    .Caption('Debugger toolbar').ToolbarPane().CloseButton(True)
                    .CaptionVisible(False)
                    .DestroyOnClose(False).Top().Row(1).Position(0)
                    .LeftDockable(False)
                    .RightDockable(False) )

        #add to the window using aui manager
        self.AddToolbar( self.dbgtools, 'Debugger toolbar', pane,
                         helpstring = 'Show/Hide the debugger toolbar' )

    def _CreateNotebook(self):
        self.notebook = EditorNotebook(self)
        #setup how to display this in the aui
        pane = aui.AuiPaneInfo()
        name='Notebook'
        pane.Name(name) #id name
        pane.CentrePane()
        #add the pane
        self.auimgr.AddPane(self.notebook,pane)

    def _CreateSearchPane(self):
        ctrl = SearchPanel(self)
        pane = aui.AuiPaneInfo()
        name='Find and Replace'
        pane.Name(name) #id name
        pane.Caption('Find and Replace')
        pane.CloseButton(True) #close button
        pane.DestroyOnClose(False)
        pane.Floatable(True)
        pane.Resizable(True)
        pane.MinSize( (-1,65))
        pane.MaxSize( (-1,65))
        pane.Bottom()
        pane.Hide()

        #add the pane and menu item (see aui frame class) and store a pane 
        #reference
        self.search= self.AddPane( ctrl, pane, None)


    def _CreateDebuggerPane(self):
        ctrl = BreakPointListPanel(self, self.tool)
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
        pane.Left()
        pane.Dock()
        pane.Hide()

        #add the pane and menu item (see aui frame class) and store a pane 
        #reference
        self.bp_pane= self.AddPane( ctrl, pane, None)

    #---Interface methods-------------------------------------------------------
    def OpenFile(self,filepath):
        """Opens the file in the editor"""
        self.notebook.OpenFile(filepath)
        self.Show()
        self.Raise()

    def GetMenu(self,menu):
        """
        Return a reference to the menu/menubar:
        menu = 'menubar','file','edit','format','view','toolbars','tools','help'
        """
        menu = menu.lower()
        if menu=='menubar':
            return self.menubar
        if menu=='file':
            return self.menubar.file_menu  #file menu
        if menu=='edit':
            return self.menubar.edit_menu  #edit menu
        if menu=='format':
            return self.menubar.format_menu  #format menu
        if menu=='view':
            return self.menubar.view_menu  #view menu
        if menu=='toolbars':
            return self.menubar.toolbars_menu  #toolbar submenu
        if menu=='tools':
            return self.menubar.tool_menu  #tool menu
        if menu=='help':
            return self.menubar.help_menu  #help menu

    def ToggleFind(self):
        """
        Show/Hide the search panel
        """
        if self.search.IsShown():
            self.search.Hide()
            page = self.notebook.GetCurrentPage()
            if page is not None:
                page.SetFocus()
        else:
            self.search.Show()
            self.search.window.SetFocus()
        self.auimgr.Update()
        
    #---Event handlers----------------------------------------------------------
    def OnClose(self,event):
        """Editor frame close event handler"""
        res = self.notebook.CloseAll()
        if res is not True:
            return

        #check if console is hidden too
        #console = self.toolmgr.get_tool('Console')
        #if console.frame.IsShown() is False:   
        #    dlg = wx.MessageDialog(self, "The Console is also hidden.\nDo you want to exit PTK?", "Hide editor",
        #    wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        #    result=dlg.ShowModal()
        #    dlg.Destroy()
        #    if result==wx.ID_YES:
        #        self.ExecFile(num)
        self.Hide()
        

    def OnFileHistory(self, event):
        filenum = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(filenum)
        self.OpenFile(path)

#-------------------------------------------------------------------------------
class EditorTools(toolpanel.ToolPanel):
    def __init__(self,parent):
        toolpanel.ToolPanel.__init__(self, parent, -1)
        self.SetStatusBar(parent.StatusBar)

        #set the icon size
        self.SetToolBitmapSize( (22,22) )

        #load some icons
        new_bmp     = common22.document_new.GetBitmap()
        open_bmp    = common22.document_open.GetBitmap()
        save_bmp    = common22.document_save.GetBitmap()

        cut_bmp     = common22.edit_cut.GetBitmap()
        copy_bmp    = common22.edit_copy.GetBitmap()
        paste_bmp   = common22.edit_paste.GetBitmap()

        undo_bmp    = common22.edit_undo.GetBitmap()
        redo_bmp    = common22.edit_redo.GetBitmap()
        search_bmp  = common22.edit_find.GetBitmap()

        untab_bmp   = editor_icons.format_indent_less.GetBitmap()
        tab_bmp     = editor_icons.format_indent_more.GetBitmap()
        com_bmp     = editor_icons.edit_comment.GetBitmap()
        uncom_bmp   = editor_icons.edit_uncomment.GetBitmap()
        sep_bmp     = editor_icons.add_separator.GetBitmap()
        
        #new
        self.AddTool( wx.ID_NEW, new_bmp,wx.ITEM_NORMAL, 
                        'Create a new file', 
                        'Create a new file to edit')
        self.Bind(wx.EVT_TOOL, self.OnNew, id=wx.ID_NEW)

        #open
        self.AddTool( wx.ID_OPEN, open_bmp, toolpanel.ITEM_DROPDOWN, 
                        'Open / Open recent',
                        'Open an existing file to edit')
        self.Bind(wx.EVT_TOOL, self.OnOpen, id=wx.ID_OPEN)

        #save
        self.AddTool( wx.ID_SAVE, save_bmp, wx.ITEM_NORMAL,
                        'Save file',
                        'Save file to disk')
        self.Bind(wx.EVT_TOOL, self.OnSave, id=wx.ID_SAVE)
        self.AddSeparator()
        
        #cut
        self.AddTool(wx.ID_CUT, cut_bmp, wx.ITEM_NORMAL,
                        'Cut',
                        'Cut selection to clipboard')
        self.Bind(wx.EVT_TOOL, self.OnCut, id=wx.ID_CUT)

        #copy
        self.AddTool(wx.ID_COPY, copy_bmp, wx.ITEM_NORMAL,
                        'Copy',
                        'Copy selection to clipboard')
        self.Bind(wx.EVT_TOOL, self.OnCopy, id=wx.ID_COPY)

        #paste
        self.AddTool(wx.ID_PASTE, paste_bmp, wx.ITEM_NORMAL,
                        'Paste',
                        'Paste selection from clipboard')
        self.Bind(wx.EVT_TOOL, self.OnPaste, id=wx.ID_PASTE)
        self.AddSeparator()

        #undo
        self.AddTool(wx.ID_UNDO, undo_bmp, wx.ITEM_NORMAL,
                        'Undo changes',
                        'Undo changes')
        self.Bind(wx.EVT_TOOL, self.OnUndo, id=wx.ID_UNDO)
        
        #redo
        self.AddTool(wx.ID_REDO, redo_bmp, wx.ITEM_NORMAL,
                        'Redo changes',
                        'Redo changes')
        self.Bind(wx.EVT_TOOL, self.OnRedo, id=wx.ID_REDO)
        self.AddSeparator()

        #search and replace
        self.AddTool(wx.ID_FIND, search_bmp, wx.ITEM_CHECK,
                        'Find and replace', 
                        'Find and replace')
        self.Bind(wx.EVT_TOOL, self.OnFind, id=wx.ID_FIND)

        #bind to the search pane events to update the toggle button
        # when shown/hidden
        search_pane = self.Parent.search
        search_pane.window.Bind( wx.EVT_SHOW, self.OnSearchShow)
        self.Realize()

    #---event handlers----------------------------------------------------------
    def OnNew(self,event):
        """New event handler"""
        self.Parent.notebook.New()

    def OnOpen(self,event):
        """Open event handler"""
        if event.IsChecked():
            #Show dropdown menu
            but = event.GetEventObject()
            
            #create a menu and add recent editor files
            menu = wx.Menu()
            self.Parent.filehistory.AddFilesToThisMenu(menu)
            menu.Bind(wx.EVT_MENU_RANGE, self.OnMenuOpen, id=wx.ID_FILE1, 
                        id2=wx.ID_FILE9)
            but.PopupMenu(menu)
        else:
            self.Parent.notebook.Open()
            
    def OnMenuOpen(self, event):
        """recent files menu handler"""
        filenum = event.GetId() - wx.ID_FILE1
        path = self.Parent.filehistory.GetHistoryFile(filenum)
        self.Parent.OpenFile(path)
        
    def OnSave(self,event):
        """Save event handler"""
        self.Parent.notebook.Save()

    def OnCut(self,event):
        """Cut event handler"""
        self.Parent.notebook.Cut()

    def OnCopy(self,event):
        """Copy event handler"""
        self.Parent.notebook.Copy()

    def OnPaste(self,event):
        """Paste event handler"""
        self.Parent.notebook.Paste()

    def OnUndo(self,event):
        """Undo event handler"""
        self.Parent.notebook.Undo()

    def OnRedo(self,event):
        """Redo event handler"""
        self.Parent.notebook.Redo()

    def OnFind(self,event):
        """Opens the find/replace pane event handler"""
        self.Parent.ToggleFind()

    def OnSearchShow(self, event):
        #The search pane has been shown/hidden
        shown = event.GetShow()
        self.ToggleTool(wx.ID_FIND, shown)
        self.Refresh()
        event.Skip()

#-------------------------------------------------------------------------------
class FormatTools(toolpanel.ToolPanel):
    def __init__(self,parent):
        toolpanel.ToolPanel.__init__(self, parent, -1)
        self.SetStatusBar(parent.StatusBar)

        self.parent = parent

        #set the icon size
        self.SetToolBitmapSize( (22,22) )

        #load some icons
        untab_bmp   = editor_icons.format_indent_less.GetBitmap()
        tab_bmp     = editor_icons.format_indent_more.GetBitmap()
        com_bmp     = editor_icons.edit_comment.GetBitmap()
        uncom_bmp   = editor_icons.edit_uncomment.GetBitmap()
        sep_bmp     = editor_icons.add_separator.GetBitmap()

        #unindent
        self.AddTool(wx.ID_UNINDENT, untab_bmp, wx.ITEM_NORMAL, 
                        'Unindent selection',
                        'Unindent selection')
        self.Bind(wx.EVT_TOOL, self.OnUndent, id=wx.ID_UNINDENT)
        
        #indent
        self.AddTool(wx.ID_INDENT, tab_bmp, wx.ITEM_NORMAL, 
                        'Indent selection',
                        'Indent selection')
        self.Bind(wx.EVT_TOOL, self.OnIndent, id=wx.ID_INDENT)
        
        #comment
        id = wx.NewId()
        self.AddTool(id, com_bmp, wx.ITEM_NORMAL, 
                        'Comment selection', 
                        'Comment selection')
        self.Bind(wx.EVT_TOOL, self.OnComment, id=id)
        
        #uncomment
        id = wx.NewId()
        self.AddTool(id, uncom_bmp, wx.ITEM_NORMAL,
                        'Uncomment selection',
                        'Uncomment selection')
        self.Bind(wx.EVT_TOOL, self.OnUnComment, id=id)
                
        #insert cell separator
        id = wx.NewId()
        self.AddTool(id, sep_bmp, wx.ITEM_NORMAL, 
                        'Insert cell separator', 
                        'Insert cell separator')
        self.Bind(wx.EVT_TOOL, self.OnInsertCellSeparator, id=id)
        
        self.Realize()

    #---event handlers----------------------------------------------------------
    def OnUndent(self,event):
        """Undent event handler"""
        self.parent.notebook.Undent()

    def OnIndent(self,event):
        """Indent event handler"""
        self.parent.notebook.Indent()

    def OnComment(self,event):
        """Comment event handler"""
        self.parent.notebook.Comment()

    def OnUnComment(self,event):
        """Uncomment event handler"""
        self.parent.notebook.UnComment()

    def OnInsertCellSeparator(self,event):
        """Insert separator event handler"""
        self.parent.notebook.InsertCellSeparator()
 
#-------------------------------------------------------------------------------
class EditorMenu(wx.MenuBar):
    def __init__(self,parent):
        wx.MenuBar.__init__(self)

        self.parent = parent

        self.file_menu       = wx.Menu()     #file menu
        self.edit_menu       = wx.Menu()     #edit menu
        self.format_menu     = wx.Menu()     #format menu
        self.view_menu       = wx.Menu()     #view menu
        self.toolbars_menu   = wx.Menu()     #  toolbar submenu
        self.layouts_menu    = wx.Menu()     #  layouts submenu
        self.tool_menu       = wx.Menu()       #tools menu
        self.help_menu       = wx.Menu()     #help menu
        
        ##add the menus to the menu bar
        self.Append(self.file_menu, "&File")
        self.Append(self.edit_menu, "&Edit")
        self.Append(self.format_menu, "&Format")
        self.Append(self.view_menu, "&View")
        self.Append(self.tool_menu, "&Tools")
        self.Append(self.help_menu, "&Help")

        ##file menu
        self.file_menu.Append(wx.ID_NEW, '&New\tCtrl+N', 'Create a new file') 
        self.file_menu.Append(wx.ID_OPEN, '&Open\tCtrl+O', 'Open a file') 
        self.file_menu.Append(wx.ID_SAVE, '&Save\tCtrl+S', 'Save the curent file') 
        self.file_menu.Append(wx.ID_SAVEAS, 'Save &As\tCtrl+Alt+S', 'Save the current file with a differnt name') 
        self.file_menu.AppendSeparator()
        self.recent_menu = wx.Menu()
        self.file_menu.AppendMenu(wx.ID_ANY, "&Recent Files", self.recent_menu)
        self.file_menu.AppendSeparator()
        self.file_menu.Append(wx.ID_CLOSE, "&Close Editor\tCtrl+H",'Closes the editor window')
        self.file_menu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q','Exit PTK')

        #event bindings
        self.parent.Bind(wx.EVT_MENU, self.OnNew, id=wx.ID_NEW)
        self.parent.Bind(wx.EVT_MENU, self.OnOpen, id=wx.ID_OPEN) 
        self.parent.Bind(wx.EVT_MENU, self.OnSave, id=wx.ID_SAVE)
        self.parent.Bind(wx.EVT_MENU, self.OnSaveAs, id=wx.ID_SAVEAS) 
        self.parent.Bind(wx.EVT_MENU, self.OnMenuClose, id=wx.ID_CLOSE)
        self.parent.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
    
        ##edit menu
        self.edit_menu.Append(wx.ID_CUT, 'Cu&t\tCtrl+X', 'Cut selection') 
        self.edit_menu.Append(wx.ID_COPY, '&Copy\tCtrl+C', 'Copy selection') 
        self.edit_menu.Append(wx.ID_PASTE, '&Paste\tCtrl+V', 'Paste from clipboard') 
        self.edit_menu.AppendSeparator()
        self.edit_menu.Append(wx.ID_UNDO, '&Undo\tCtrl+Z', 'Undo past actions') 
        self.edit_menu.Append(wx.ID_REDO, '&Redo\tCtrl+Y', 'Redo undone actions') 
        self.edit_menu.AppendSeparator()
        self.edit_menu.Append(wx.ID_REPLACE, '&Find and replace\tCtrl+F', 'Open the find pane')
        #event bindings
        self.parent.Bind(wx.EVT_MENU, self.OnCut, id=wx.ID_CUT)
        self.parent.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY) 
        self.parent.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.parent.Bind(wx.EVT_MENU, self.OnUndo, id=wx.ID_UNDO)
        self.parent.Bind(wx.EVT_MENU, self.OnRedo, id=wx.ID_REDO)  
        self.parent.Bind(wx.EVT_MENU, self.OnFind, id=wx.ID_REPLACE) 

        ##format menu
        indentid=wx.NewId()
        self.format_menu.Append(indentid, 'Indent\tTab', 'Indent selection')
        undentid=wx.NewId()
        self.format_menu.Append(undentid, 'Undent\tShift+Tab', 'Undent selection') 
        comid=wx.NewId()
        self.format_menu.Append(comid, 'Comment\tCtrl+#', 'Comment selection') 
        uncomid=wx.NewId()
        self.format_menu.Append(uncomid, 'Uncomment\tCtrl+Shift+#', 'Uncomment selection') 
        self.format_menu.AppendSeparator()
        sepid=wx.NewId()
        self.format_menu.Append(sepid, 'Insert cell separator\tCtrl+Enter', 'Insert a separator comment')
        #event bindings
        self.parent.Bind(wx.EVT_MENU, self.OnIndent, id=indentid) 
        self.parent.Bind(wx.EVT_MENU, self.OnUndent, id=undentid) 
        self.parent.Bind(wx.EVT_MENU, self.OnComment, id=comid) 
        self.parent.Bind(wx.EVT_MENU, self.OnUnComment, id=uncomid) 
        self.parent.Bind(wx.EVT_MENU, self.OnInsertCellSeparator, id=sepid) 
        
        ##view menu
        self.view_menu.AppendSubMenu(self.toolbars_menu , 'Toolbars...','Show Toolbars')
        self.view_menu.AppendSubMenu(self.layouts_menu , 'Layouts...','Save/Restore window layouts')
        self.view_menu.AppendSeparator()
        #layouts added in auimix

        ##tools menu
        #Run selection in current engine
        item = wx.MenuItem( self.tool_menu, ID_RUNMENU_SEL,
                            'Run selection/cell in current engine \tF9', 
                            'Run the selected code or current cell in the current engine as if typed at the console',
                            wx.ITEM_NORMAL)
        item.SetBitmap(console_icons.run_sel.GetBitmap())
        self.tool_menu.AppendItem(item)
        self.parent.Bind(wx.EVT_MENU, self.OnRunSelection, id=ID_RUNMENU_SEL) 
        self.parent.Bind(wx.EVT_UPDATE_UI, self.OnUpdateRunSel, id = ID_RUNMENU_SEL)

        #run in current engine
        item = wx.MenuItem( self.tool_menu, ID_RUNMENU_CUR, 
                                'Run file in current engine \tF10', 
                                'Run the file in the current engine',
                                 wx.ITEM_NORMAL) 
        item.SetBitmap(console_icons.run.GetBitmap())
        self.tool_menu.AppendItem(item)
        self.parent.Bind(wx.EVT_MENU, self.OnRunFile, id=ID_RUNMENU_CUR) 

        #run in new engine
        item = wx.MenuItem( self.tool_menu, ID_RUNMENU_NEW, 
                                'Run file in a new engine \tF11', 
                                'Run file in a new engine',
                                 wx.ITEM_NORMAL) 
        item.SetBitmap(console_icons.run_neweng.GetBitmap())
        self.tool_menu.AppendItem(item)
        self.parent.Bind(wx.EVT_MENU, self.OnRunNewEng, id=ID_RUNMENU_NEW)

        #Run in external process
        item = wx.MenuItem( self.tool_menu, ID_RUNMENU_EXT, 
                                'Run file as an external process \tF12', 
                                'Run file as an external process',
                                 wx.ITEM_NORMAL) 
        item.SetBitmap(console_icons.run_ext.GetBitmap())
        self.tool_menu.AppendItem(item)
        self.parent.Bind(wx.EVT_MENU, self.OnRunExt, id=ID_RUNMENU_EXT) 

        ##help menu
        self.help_menu.Append(wx.ID_HELP, 'Help', 'Open the python documentation...') 
        tipid=wx.NewId()
        self.help_menu.Append(tipid, 'Show tips', 'Show tips') 
        self.help_menu.Append(wx.ID_ABOUT, 'About...', 'About this program...') 
        #bindings
        self.parent.Bind(wx.EVT_MENU, self.OnHelp, id=wx.ID_HELP)
        self.parent.Bind(wx.EVT_MENU, self.OnTip, id=tipid)
        self.parent.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)

    #---Event handlers----------------------------------------------------------
    #file menu
    def OnNew(self,event):
        """New file event handler"""
        self.parent.notebook.New()

    def OnOpen(self,event):
        """Open file event handler"""
        self.parent.notebook.Open()

    def OnSave(self,event):
        """Save file event handler"""
        self.parent.notebook.Save()

    def OnSaveAs(self,event):
        """Save as event handler"""
        self.parent.notebook.SaveAs()

    def OnMenuClose(self,event):
        """Menu close event handler"""
        self.parent.Close()

    def OnExit(self, event):
        """Called when exit menu item selected"""
        app = wx.GetApp()
        app.Exit()

    #edit menu
    def OnCut(self,event):
        """Edit.Cut event handler"""
        self.parent.notebook.Cut()

    def OnCopy(self,event):
        """Edit.Copy event handler"""
        self.parent.notebook.Copy()

    def OnPaste(self,event):
        """Edit.Paste event handler"""
        self.parent.notebook.Paste()

    def OnUndo(self,event):
        """Edit.Undo event handler"""
        self.parent.notebook.Undo()

    def OnRedo(self,event):
        """Edit.Redo event handler"""
        self.parent.notebook.Redo()

    def OnIndent(self,event):
        """Edit.Indent event handler"""
        self.parent.notebook.Indent()

    def OnUndent(self,event):
        """Edit.Undent event handler"""
        self.parent.notebook.Undent()

    def OnComment(self,event): 
        """Edit.Comment event handler"""
        self.parent.notebook.Comment()

    def OnUnComment(self,event):
        """Edit.UnComment event handler"""
        self.parent.notebook.UnComment()

    def OnInsertCellSeparator(self,event):
        """Edit.Insert Separator event handler"""
        self.parent.notebook.InsertCellSeparator()
        
    def OnFind(self,event):
        """Opens the find/replace pane event handler"""
        self.parent.ToggleFind()

    #view menu
    #done in auimixin

    #tools menu
    def OnRunSelection(self,event):
        """Run selection event handler"""
        self.parent.notebook.Run()

    def OnUpdateRunSel(self, event):
        """Enable/disable the run selection menu item"""
        num = self.parent.notebook.GetSelection()
        if num==-1:
            enable = False
        else:
            page = self.parent.notebook.GetPage(num)
            cmd  = page.GetSelectedText()
            if len(cmd)==0:
                enable = False
            else:
                enable = True
        #self.tool_menu.Enable(ID_RUNMENU_SEL, enable)

    #tools menu
    def OnRunFile(self,event):
        """Run file (execfile) event handler"""
        self.parent.notebook.ExecFile()

    def OnRunExt(self,event):
        """Run as external process event handler"""
        self.parent.notebook.ExtRun()

    def OnRunNewEng(self, event):
        """Run as new engine event handler"""
        self.parent.notebook.RunNewEngine()

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
