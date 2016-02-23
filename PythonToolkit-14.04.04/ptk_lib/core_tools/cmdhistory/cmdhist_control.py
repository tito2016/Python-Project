"""
Command History control

This is the panel class that is added as a pane to the Console window.
It recieves all CmdHistory.* messages and stores the command history log.
"""

#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import os
import wx                           #for gui elements
import wx.stc                       #styled text control
import keyword                  

from ptk_lib.resources import common16
from ptk_lib.controls import toolpanel

from ptk_lib.core_tools.fileio import FileDrop

#---main control----------------------------------------------------------------
class CmdHistControl(wx.Panel):
    def __init__(self,parent, cmdhist):
        wx.Panel.__init__(self, parent, id=-1)

        self.cmdhist = cmdhist

        sizer = wx.BoxSizer(wx.VERTICAL)
        #create toolbar
        self._CreateTools()
        sizer.Add(self.tools, 0, wx.EXPAND,0 )

        #create the history stc
        self.stc = CmdHistPage(self,-1, self.cmdhist)
        sizer.Add(self.stc,1,wx.EXPAND|wx.ALL,0)
        self.SetSizer(sizer)
    
    def _CreateTools(self):
        """Creates the toolbar panel in the browser"""
        
        self.tools = toolpanel.ToolPanel(self,-1)
        #set the status bar
        console = self.cmdhist.toolmgr.get_tool('Console')
        self.tools.SetStatusBar(console.frame.StatusBar)

        #set the icon size
        self.tools.SetToolBitmapSize((16,16))

        #load some icons
        save_bmp    = common16.document_save.GetBitmap()
        open_bmp    = common16.document_open.GetBitmap()
        clear_bmp   = common16.edit_delete.GetBitmap()

        #save
        id = wx.NewId()
        self.tools.AddTool(id, save_bmp, wx.ITEM_NORMAL,
                            shortHelp='Export command history',
                            longHelp='Export the command history')
        self.Bind(wx.EVT_TOOL, self.OnSave, id=id)
        
        #load
        id = wx.NewId()
        self.tools.AddTool(id, open_bmp, wx.ITEM_NORMAL,
                            shortHelp='Import command history',
                            longHelp='Import a command history')
        self.Bind(wx.EVT_TOOL, self.OnLoad, id=id)
        self.tools.AddSeparator()

        #clear
        id = wx.NewId()
        self.tools.AddTool(id, clear_bmp, wx.ITEM_NORMAL,
                            shortHelp='Clear the command history',
                            longHelp='Clears the command history')
        self.Bind(wx.EVT_TOOL, self.OnClear ,id=id)
        self.tools.AddSeparator()

        #search
        self.search = wx.SearchCtrl(self.tools, size=(200,-1), style=wx.TE_PROCESS_ENTER)
        self.tools.AddControl(self.search)
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnSearch, self.search)
        #self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnCancel, self.search)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearch, self.search)
        self.Bind(wx.EVT_TEXT, self.OnSearch, self.search)      

    #---events------------------------------------------------------------------
    def OnSave(self,evt):
        app = wx.GetApp()
        dlg = wx.FileDialog(
                self, message='Export command history to file',
                defaultDir=os.getcwd(),
                defaultFile="cmdhist",
                wildcard = "python source (*.py)|*.py|History file (*.hist)|*.hist",
                style= wx.SAVE | wx.OVERWRITE_PROMPT
                )
        #only save if not cancelled.
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        #get the path
        path = dlg.GetPath()
        #check type to save
        exttype=dlg.GetFilterIndex()
        if exttype==0:
            self.stc.SaveFile(path)
        else:
            self.cmdhist.SaveHistory(path)
        dlg.Destroy()

    def OnLoad(self,evt):
        #Create the file open dialog.
        app = wx.GetApp()
        dlg = wx.FileDialog(
            self, message="Import command history",
            defaultDir=os.getcwd(), 
            defaultFile="",
            wildcard = "python source (*.py)|*.py|History file (*.hist)|*.hist",
            style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR )

        #check for ok
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        # This returns a list of files that were selected.
        paths = dlg.GetPaths()
        dlg.Destroy()

        #load each file
        for path in paths:
            self.cmdhist.ImportHistory(path)

    def OnClear(self,evt):
        msg = "Clear the command history?"
        dlg = wx.MessageDialog(self, msg, "Clear command history",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.cmdhist.ClearHistory()
        dlg.Destroy()

    def OnSearch(self,evt):
        text = self.search.GetValue()
        self.stc.FindNext(text,flags=0)

#---History page-----------------------------------------------------------------
class CmdHistPage(wx.stc.StyledTextCtrl):
    def __init__(self, parent, id, cmdhist):
        wx.stc.StyledTextCtrl.__init__(self, parent, id)

        self.cmdhist = cmdhist
        
        #create a droptarget
        self.dt = FileDrop()
        self.SetDropTarget(self.dt)  

        #setup the stc
        self._initSTC()

        #bind events
        self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        # Assign handler for the context menu and edit events
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnCMenuUpdateUI)
        self.ID_RUN = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnRun, id=self.ID_RUN)
        self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
        self.ID_SELECTLINE = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnSelectLine, id=self.ID_SELECTLINE)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=wx.ID_SELECTALL)

        #register for command history messages
        self.cmdhist.msg_node.subscribe('Console.CmdHistory.Add',self.msg_hist_add)
        self.cmdhist.msg_node.subscribe('Console.CmdHistory.Changed',self.msg_hist_changed)

        self._updateSTC()

    def _updateSTC(self):
        #clear the stc
        self.ClearAll()
        #load the commands from history
        for cmd in self.cmdhist.hist:
            self.InsertText(0,cmd+'\n')
        #scroll to bottom
        self.SetCurrentPos(self.GetLength()) 
        self.EnsureCaretVisible()
        self.SetAnchor(self.GetLength())


    def _initSTC(self):
        # Set the fonts
        faces = { 
              'times': 'Courier New',
              'mono' : 'Courier New',
              'helv' : 'Courier New',
              'other': 'Courier New',
              'size' : 10,
              'backcol'   : '#FFFFFF',
            }
        self.SetUndoCollection(False) #disable undo
        self.SetKeyWords(0, " ".join(keyword.kwlist))
        self.SetLexer(wx.stc.STC_LEX_PYTHON) #need to print lines longer than 64k!!!
        self.SetWrapMode(False)
    
        # Enable folding
        self.SetProperty("fold", "1" ) 
        
        # Indentation and tab stuff
        self.SetIndent(4)               # Proscribed indent size for wx
        self.SetIndentationGuides(True) # Show indent guides
        self.SetTabIndents(True)        # Tab key indents
        self.SetTabWidth(4)             # Proscribed tab size for wx
        self.SetUseTabs(False)          # Use spaces rather than tabs, or
                                        # TabTimmy will complain!
        self.SetViewWhiteSpace(False)   # Don't view white space  
        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetViewEOL(False)
        
        # No right-edge mode indicator
        self.SetEdgeMode(wx.stc.STC_EDGE_NONE)

        # Setup a margin to hold fold markers
        self.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(1, wx.stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(1, True)
        self.SetMarginWidth(1, 12)

        # Fold symbols Like a flattened tree control using square headers
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,    wx.stc.STC_MARK_BOXMINUS,          "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,        wx.stc.STC_MARK_BOXPLUS,           "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     wx.stc.STC_MARK_VLINE,             "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,    wx.stc.STC_MARK_LCORNER,           "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,     wx.stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, wx.stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, wx.stc.STC_MARK_TCORNER,           "white", "#808080")

        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FF0000,bold")

        # Python styles
        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Default 
        self.StyleSetSpec(wx.stc.STC_P_DEFAULT, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
        # Comments
        self.StyleSetSpec(wx.stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(other)s,size:%(size)d" % faces)
        # Number
        self.StyleSetSpec(wx.stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        self.StyleSetSpec(wx.stc.STC_P_STRING, "fore:#7F007F,face:%(helv)s,size:%(size)d" % faces)
        # Single quoted string
        self.StyleSetSpec(wx.stc.STC_P_CHARACTER, "fore:#7F007F,face:%(helv)s,size:%(size)d" % faces)
        # Keyword
        self.StyleSetSpec(wx.stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        self.StyleSetSpec(wx.stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        self.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        self.StyleSetSpec(wx.stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
        self.StyleSetSpec(wx.stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        self.StyleSetSpec(wx.stc.STC_P_OPERATOR, "size:%(size)d" % faces)
        # Identifiers
        self.StyleSetSpec(wx.stc.STC_P_IDENTIFIER, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
        # Comment-blocks
        self.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK, "fore:#CC0000,size:%(size)d" % faces)
        # End of line where string is not closed
        self.StyleSetSpec(wx.stc.STC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)

        # Selection background
        self.SetCaretForeground("BLUE")
        self.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
    #---Interfaces--------------------------------------------------------------
    def FoldAll(self):
        expanding=False
        lineCount = self.GetLineCount()

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break
        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & wx.stc.STC_FOLDLEVELHEADERFLAG and \
               (level & wx.stc.STC_FOLDLEVELNUMBERMASK) == wx.stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & wx.stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def Run(self):
        """Runs the selected text in the console"""
        cmd  = self.GetSelectedText()
        #check if there is any selection
        if len(cmd)==0:
            return
        #strip any \n from the lines
        if cmd[-1]=='\n':
            cmd = cmd[:-1]
        #get the console tool
        con_tool = wx.GetApp().toolmgr.get_tool('Console')
        console = con_tool.get_current_engine()
        if console is not None:
           console.exec_source( cmd )

    #overload these to avoid cutting/pasting into the history log
    def Cut(self):
        pass
    def Paste(self):
        pass

    def FindNext(self,text,flags=0):
        """Find the next occurance of the text"""
        #set the search anchor
        pos = self.GetCurrentPos()
        if pos==self.GetLength():
            self.SetCurrentPos(0)
        else:
            self.SetCurrentPos(pos+1)

        self.SearchAnchor()
        spos = self.SearchNext(flags,text)
        self.EnsureCaretVisible()
        if spos==-1:
            self.SetCurrentPos(pos)
            return False
        else:
            return True

    #---Events------------------------------------------------------------------
    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 1:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)


    def OnKeyPressed(self, event):
        """Handle key presses in the page"""
        key = event.GetKeyCode()
        #run the code
        if key==wx.WXK_F9:
            self.Run()

    def OnContextMenu(self, evt):
        """Create and display a context menu for the shell"""
        menu = wx.Menu()
        menu.Append(self.ID_RUN, "Run")
        menu.Append(wx.ID_COPY, "Copy")
        menu.AppendSeparator()
        menu.Append(self.ID_SELECTLINE, "Select Line")
        menu.Append(wx.ID_SELECTALL, "Select All")
        self.PopupMenu(menu)

    def OnCMenuUpdateUI(self, evt):
        """disable the context menu actions that are not possible"""
        id = evt.Id
        if id == self.ID_RUN:
            evt.Enable(self.GetSelectionStart() != self.GetSelectionEnd())

    def OnCopy(self,evt):
        self.Copy()

    def OnRun(self,evt):
        self.Run()

    def OnSelectLine(self,evt):
        n=self.GetCurrentLine()
        start = self.PositionFromLine(n)
        end   = self.GetLineEndPosition(n)
        self.SetSelection(start,end)

    def OnSelectAll(self,evt):
        self.SelectAll()

    #---messages----------------------------------------------------------------
    def msg_hist_add(self,msg):
        """A command was added to the command history add it to the stc"""
        cmd, = msg.get_data()
        self.AppendText(cmd+'\n')

    def msg_hist_changed(self,msg):
        """Command history was changed (new file loaded) refresh the stc"""
        self._updateSTC()
