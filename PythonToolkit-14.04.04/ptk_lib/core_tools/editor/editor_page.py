"""
The editor page is a customised wx.STC control which represents a file in the 
editor. The class has methods to perform actions on the text such as indent,
comment, run etc.
"""
#---Imports---------------------------------------------------------------------
import keyword                  
import textwrap                     #standard libary text wrapping utils

import wx                           #for gui elements
import wx.stc                       #styled text control

from ptk_lib.core_tools.fileio import FileDrop
from dbg_controls import EditBreakpointDialog

class CellDialog(wx.Dialog):
    def __init__(self, parent, id=-1):
        wx.Dialog.__init__(self, parent, id, size=(350,220))
        self.SetTitle('Insert code cell separator')

        vbox = wx.BoxSizer(wx.VERTICAL)

        text = wx.StaticText(self, -1, 'Enter code cell label:')
        vbox.Add( text, 0, wx.ALL,5)
        self.label = wx.TextCtrl( self, -1, '', style=wx.TE_MULTILINE)
        vbox.Add( self.label, 1, wx.ALL|wx.EXPAND, 10)

        self.style = wx.RadioBox(self, -1, "Style", choices=['full (multiline)', 'compact (single line)'], 
                                    majorDimension=0, style=wx.RA_HORIZONTAL)
        vbox.Add( self.style, 0, wx.ALL|wx.EXPAND, 5)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        vbox.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,10)

        self.ok_but  = wx.Button(self, wx.ID_OK, "OK")
        self.cancel_but = wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( self.ok_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( self.cancel_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        vbox.Add(butsizer,0, wx.ALL|wx.ALIGN_RIGHT)

        self.SetSizer(vbox)

    def GetValue(self):
        """
        Return the comment string to use for the new code cell.
        """
        label = self.label.GetValue()
        style = self.style.GetSelection()

        if style==0:
            #wrap the label
            wlabel = '\n# '.join( textwrap.wrap( label, 78) )

            #add the separator
            string = '#%%'+('-'*77)+'\n# '+wlabel+'\n'+'#'+('-'*79)+'\n'
        else:
            string = '#%% '+label+'\n'
        return string


#---Editor page-----------------------------------------------------------------
class EditorPage(wx.stc.StyledTextCtrl):
    def __init__(self, parent, id=-1):
        wx.stc.StyledTextCtrl.__init__(self, parent, id, style=0)

        #internal attributes
        self._filename = ''
        self._bpmarkers = {}   #store breakpoint marker handles {bpid: handle}
        self._bpmode = 2       #bp mode (0=disabled, 1=enabled & modified, 2=enabled and unmodified)

        #setup the stc
        self._initSTC()

        #create a droptarget to handle file drops (via the parent notebook.
        self.dt = FileDrop(parent.OpenFile)
        self.SetDropTarget(self.dt)  

        #bind events
        self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        self.Bind(wx.stc.EVT_STC_SAVEPOINTLEFT, self.OnSavePointLeft)
        self.Bind(wx.stc.EVT_STC_SAVEPOINTREACHED, self.OnSavePointReached)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def _initSTC(self):
        #lexer is python, keywords are python commands?
        self.SetLexer(wx.stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        # Enable folding
        self.SetProperty("fold", "1" ) 
        
        # Highlight tab/space mixing (shouldn't be any)
        self.SetProperty("tab.timmy.whinge.level", "4")
        
        # Set left and right margin widths in pixels 
        self.SetMargins(2,2)

        # Margin #0 - Set up the numbers in the margin
        self.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
        self.SetMarginMask(0, 0) #only show line numbers
        self.SetMarginWidth(0, 40)

        # Margin #1 - breakpoint symbols
        self.SetMarginType(1, wx.stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(1, ~wx.stc.STC_MASK_FOLDERS) #do not show fold symbols
        self.SetMarginSensitive(1, True)
        self.SetMarginWidth(1, 12)

        #set the breakpoint symbols
        self.UpdateBreakpointSymbols()
        #paused at marker
        self.MarkerDefine(1, wx.stc.STC_MARK_SHORTARROW, "BLACK", "GREEN")

        # Margin #2 - holds fold markers
        self.SetFoldFlags(16)
        self.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, wx.stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)
       
        # Fold symbols Like a flattened tree control using square headers
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,    wx.stc.STC_MARK_BOXMINUS,          "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,        wx.stc.STC_MARK_BOXPLUS,           "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     wx.stc.STC_MARK_VLINE,             "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,    wx.stc.STC_MARK_LCORNER,           "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,     wx.stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, wx.stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, wx.stc.STC_MARK_TCORNER,           "white", "#808080")

        # Indentation and tab stuff
        self.SetIndent(4)               # Proscribed indent size for wx
        self.SetIndentationGuides(True) # Show indent guides
        self.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
        self.SetTabIndents(True)        # Tab key indents
        self.SetTabWidth(4)             # Proscribed tab size for wx
        self.SetUseTabs(False)          # Use spaces rather than tabs, or
                                        # TabTimmy will complain!
        self.SetViewWhiteSpace(False)   # Don't view white space  
                                     
        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.            
        self.SetEOLMode(wx.stc.STC_EOL_LF)
        self.SetViewEOL(False)
        
        # right-edge mode indicator
        self.SetEdgeMode(wx.stc.STC_EDGE_LINE)
        self.SetEdgeColumn(80)

        #self.SetBufferedDraw(False)
        #self.SetUseAntiAliasing(True)

        faces = {   'times': 'Courier New',
                    'mono' : 'Courier New',
                    'helv' : 'Courier New',
                    'other': 'Courier New',
                    'size' : 10
                }

        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FF0000,bold")

        # Python styles
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

        self.SetCaretForeground("BLUE")
        #Selection background
        self.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

        #set what will cause a EVT_CHANGE/EVT_MODIFIED
        self.SetModEventMask(   wx.stc.STC_MOD_INSERTTEXT| wx.stc.STC_MOD_DELETETEXT| wx.stc.STC_MOD_CHANGESTYLE|
                                wx.stc.STC_MOD_DELETETEXT| wx.stc.STC_PERFORMED_USER| 
                                wx.stc.STC_PERFORMED_UNDO| wx.stc.STC_PERFORMED_REDO| wx.stc.STC_LASTSTEPINUNDOREDO )
    
    #---Interfaces--------------------------------------------------------------
    def LoadFile(self, filename):
        """
        Load the contents of filename into the editor.
        """
        res = wx.stc.StyledTextCtrl.LoadFile(self,filename)
        if res is False:
            return False
        self._filename = filename
        self.SetSavePoint()
        #add breakpoint markers done in SavePointReached event handler
        return res

    def SaveFile(self, filename):
        """
        Write the contents of the editor to the filename.
        """
        self._filename = filename

        #modify breakpoints to use the new filename.
        editor = wx.GetApp().toolmgr.get_tool('Editor')
        for bpid in self._bpmarkers:

            #get the breakpoint
            bp = editor.get_breakpoint(bpid)
            #and marker handle
            hnd = self._bpmarkers[bpid]
            
            #dictionary of modifications.
            mods = {}

            #check filename
            if bp['filename']!=filename:
                mods['filename'] = filename
            #check lineno
            lineno = self.MarkerLineFromHandle(hnd)
            
            if bp['lineno']!=(lineno+1):
                #stc lineno start at 0 (1 in margins display) - debugger lineno start at 1.
                mods['lineno']=(lineno+1)
            
            #do any modification necessary
            if len(mods)!=0:
                editor.modify_breakpoint( bpid, **mods )

        #make sure that breakpoints show as unmodified/active
        self.UpdateBreakpointSymbols()

        #do save last - as otherwise EVT_STC_SAVEPOINTREACHED is called and 
        #resets all the breakpoints
        res = wx.stc.StyledTextCtrl.SaveFile(self,filename)
        if res is False:
            return False
        return True

    def Indent(self):
        """Indent the selected lines"""
        self.CmdKeyExecute(wx.stc.STC_CMD_TAB)

    def Undent(self):
        """Undent the selected lines"""
        self.CmdKeyExecute(wx.stc.STC_CMD_BACKTAB)

    def Comment(self):
        """Comment out the selected lines"""
        sel = self.GetSelection()
        start = self.LineFromPosition(sel[0])
        end = self.LineFromPosition(sel[1])
        if start>end: #swap around
            start,end=end,start
        #start an undo mark
        self.BeginUndoAction()
        for ln in range(start, end + 1):
            linestart = self.PositionFromLine(ln)
            self.InsertText(linestart, '#')
        #finish the undo mark
        self.EndUndoAction()

    def UnComment(self):
        """UnComment out the selected lines"""
        sel = self.GetSelection()
        start = self.LineFromPosition(sel[0])
        end = self.LineFromPosition(sel[1])
        if start>end: #swap around
            start,end=end,start
        #start an undo mark
        self.BeginUndoAction()
        for ln in range(start, end + 1):
            linestart = self.PositionFromLine(ln)
            if chr(self.GetCharAt(linestart)) == '#':
                #set cursor to the right of the #
                self.SetCurrentPos(linestart + 1)
                #delete to the beginning of th line
                self.DelLineLeft()
        #finish the undo mark
        self.EndUndoAction()

    def FindNext(self,text,flags):
        """Find the next occurance of the text"""
        #set the search anchor
        pos = self.GetCurrentPos()
        if pos!=self.GetLength():
            self.SetCurrentPos(pos+1)
        self.SearchAnchor()
        spos = self.SearchNext(flags,text)
        self.EnsureCaretVisible()
        if spos==-1:
            self.SetCurrentPos(pos)
            return False
        else:
            return True

    def FindPrevious(self,text,flags):
        """Find the previous occurance of the text"""
        #set the search anchor
        pos = self.GetCurrentPos()
        if pos!=0:
            self.SetCurrentPos(pos-1)
        self.SearchAnchor()
        spos = self.SearchPrev(flags,text)
        self.EnsureCaretVisible()
        if spos==-1:
            self.SetCurrentPos(pos)
            return False
        else:
            return True

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
    #---cells-------------------------------------------------------------------
    def InsertCellSeparator(self):
        """Insert a code cell separator comment"""
        #dlg = wx.TextEntryDialog(self, 'Enter code cell separator label text:',
        #            'Insert code cell separator', '')
        dlg = CellDialog(self, -1)

        if dlg.ShowModal() == wx.ID_OK:
            label = dlg.GetValue()

            #If not at the start of a line add \n
            pos    = self.GetCurrentPos()
            indent = self.GetColumn(pos)
            if indent!=0:
                self.InsertText(pos,'\n')
                self.SetCurrentPos(pos+1)

            #add the separator
            pos    = self.GetCurrentPos()
            line   = self.LineFromPosition(pos)
            pos    = self.PositionFromLine(line)
            self.InsertText(pos,label)

            #move to end of separator
            self.SetCurrentPos(pos+len(label))
            self.SetAnchor(pos+len(label))

        dlg.Destroy()

    def GetCurrentCell(self):
        """
        Returns the content of the current cell or None if not in a cell.
        """
        pos = self.GetCurrentPos()
        cell_start =  self.FindText(pos,0,'#%%',flags=0)
        if cell_start == -1:
            return None

        cell_end   =  self.FindText(pos, self.GetLength(),'#%%',flags=0)
        if cell_end == -1:
            cell_end = self.GetLength()
        cell = self.GetTextRange(cell_start, cell_end)
        return cell

    #---Called by Editor tool to manage breakpoints-----------------------------
    def UpdateBreakpointSymbols(self):
        """
        Update the breakpoint marker symbols in this page.
            mode = 0    -   Debugger disabled / no active engine.
                            (white circles - breakpoint will be ignored)
            mode = 1    -   Debugger enabled - but file modified lineno could
                            be inconsistant.
                            (yellow circles - breakpoint may work)
            mode = 2    -   Debugger enabled and file unmodified.
                            (red circles - breakpoint will work)
        """
        #check file modified
        mod = self.GetModify()
        
        #check current engines debugger state: on/off
        console = wx.GetApp().toolmgr.get_tool('Console')
        eng = console.get_current_engine()
        if eng is None:
            debug = False
        else:
            debug = eng.debug
        
        #decide mode to use.
        if debug is False:
            mode = 0    #white - breakpoints disabled
        elif mod is True:
            mode = 1    #yellow - breakpoint lineno may be wrong
        else:
            mode = 2    #red - breakpoints active

        #already set do nothing.
        if mode == self._bpmode:
            return

        #set the markers
        if mode==0:
            self._bpmode = 0
            #set the bp markers to grey
            self.MarkerDefine(0, wx.stc.STC_MARK_CIRCLE, "BLACK", "WHITE")
        elif mode==1:
            self._bpmode = 1
            #set the bp markers to yellow
            self.MarkerDefine(0, wx.stc.STC_MARK_CIRCLE, "BLACK", "YELLOW")
        elif mode==2:
            self._bpmode = 2
            #set the bp markers to red
            self.MarkerDefine(0, wx.stc.STC_MARK_CIRCLE, "BLACK", "RED")

    def AddBreakpointMarker(self, bpid, lineno):
        """
        Add marker for the breakpoint with bpid given.
        - Called by the Editor tool when a breakpoint is set in this file.
        """
        #cannot have breakpoints as file is not saved.
        if self._filename is '':
            #todo show an error?
            return

        #note: linenos in debugger/margin display start at 1 but here in stc 
        #methods start at 0! hence the lineno-1

        #check if the breakpoint already has a marker
        if bpid in self._bpmarkers:
            return

        #add a new marker at this line
        hnd = self.MarkerAdd(lineno-1, 0)

        #store the marker handle with the breakpoint id.
        self._bpmarkers[bpid] = hnd

    def DeleteBreakpointMarker(self, bpid):
        """
        Delete the marker for the breakpoint with bpid given.
        - Called by the Editor tool when a breakpoint is clear in this file.
        """
        #get breakpoint marker handle
        hnd = self._bpmarkers.pop( bpid, None)

        #remove the maker
        if hnd is not None:
            self.MarkerDeleteHandle(hnd)

    def DeleteAllBreakpointMarkers(self):
        """
        Delete all breakpoint markers.
        - Called by the Editor tool when allbreakpoints are cleared
        """
        self._bpmarkers = {}
        self.MarkerDeleteAll(0)

    def RefreshBreakpointMarkers(self, bps=None):
        """
        Remove and re-add breakpoint markers.
        - Called when loading a file, or when a save  point is reached to 
        ensure markers are shown in correct positions.
        """
        #add any breakpoints that are set for this new file.
        editor = wx.GetApp().toolmgr.get_tool('Editor')

        bps = editor.get_breakpoints(self._filename)
        
        #remove all breakpoint markers and readd for the current breakpoints.
        self.MarkerDeleteAll(0)
        self._bpmarkers = {}

        #add new markers
        for bp in bps:
            hnd = self.MarkerAdd(bp['lineno']-1, 0)
            self._bpmarkers[bp['id']] = hnd

        #make sure the markers show unmodified/active
        self.UpdateBreakpointSymbols()


    #---Called internally to manage breakpoints---------------------------------
    def SetBreakpoint(self, lineno):
        """
        Set a new breakpoint at the line number given.
        
        - Editor tool sets the breakpoint in all engines
        - Calls AddBreakpointMarker to add a marker for the new breakpoint
        """
        #cannot set a breakpoint as file not saved.
        if self._filename is '':
            #todo show an error?
            return

        #get a reference to the engine manager
        app = wx.GetApp()
        editor = app.toolmgr.get_tool('Editor')
        editor.set_breakpoint(self._filename,(lineno+1),
                        condition=None,ignore_count=None,trigger_count=None)
        #note: linenos in debugger/margin display start at 1 but here in stc methods start at 0!
        #       hence the lineno+1
        # marker added by editor tool via AddBreakpointMarker()

    def EditBreakpoint(self, lineno):
        """
        Edit existing breakpoint(s) at the line number given. This will edit any
        breakpoints at this line even if the file has yet to be saved.
        """
        #loop over breakpoint markers in this file and check lineno
        bpids = []
        for bpid in self._bpmarkers.keys():
            #check the line of this breakpoint marker
            hnd = self._bpmarkers[bpid]
            line = self.MarkerLineFromHandle(hnd)
            if line == lineno:
                bpids.append(bpid)

        #open the edit breakpoint dialog
        dlg = EditBreakpointDialog( self, self._filename, bpids )
        res = dlg.ShowModal()
        dlg.Destroy()

    def ClearBreakpoint(self, lineno):
        """
        Clear any existing breakpoints at the line number given.
        """
        #get the editor tool
        editor = wx.GetApp().toolmgr.get_tool('Editor')

        #loop over breakpoint markers in this file and clear if at this line
        for bpid in self._bpmarkers.keys():
            #check the line of this breakpoint
            hnd = self._bpmarkers[bpid]
            line = self.MarkerLineFromHandle(hnd)
            if line == lineno:
                editor.clear_breakpoint( bpid )
        # Note: marker deleted by editor tool via DeletedBreakpointMarker()

    def _bit_set(self,mask, n):
        """
        Check if the nth bit is set in a 32bit mask    
        use to check marker flags (mask is 32bit int indicating the pressence of a 
        marker types 0-31
        """
        bs = bin(mask)[2:].rjust(32,'0')
        bs = bs[::-1]
        if bs[n]=='1':
            return True
        else:
            return False

    #---Events------------------------------------------------------------------
    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == wx.stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == wx.stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)

    def OnMarginClick(self, evt):
        margin =  evt.GetMargin()
        shiftdown = evt.GetShift()
        ctrldown = evt.GetControl()
        lineClicked = self.LineFromPosition(evt.GetPosition())

        # set/edit/delete a breakpoint
        if margin==0 or margin==1: 

            #check if a breakpoint marker is at this line
            bpset = self._bit_set( self.MarkerGet(lineClicked) , 0)

            if (bpset is False):
                #No breakpoint at this line, add one
                self.SetBreakpoint( lineClicked )
                if ctrldown is True:
                    #edit new breakpoint
                    self.EditBreakpoint( lineClicked )

            elif (bpset is True) and (ctrldown is True):
                self.EditBreakpoint( lineClicked )
            else:
                self.ClearBreakpoint( lineClicked )

        # fold and unfold as needed
        elif evt.GetMargin() == 2:
            if shiftdown and ctrldown:
                self.FoldAll()
            else:
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

    def OnSavePointReached(self, event):
        """
        Handler for EVT_STC_SAVEPOINTREACHED
        """
        self.UpdateBreakpointSymbols()
        self.RefreshBreakpointMarkers()
        event.Skip()

    def OnSavePointLeft(self, event):
        """
        Handler for EVT_STC_SAVEPOINTLEFT
        """
        self.UpdateBreakpointSymbols()
        event.Skip()
        
    def OnKeyDown(self, event):
        """Key down event handler."""

        #If the auto-complete window is up let it handle the key
        if self.AutoCompActive():
            event.Skip()
            return
    
        #close any open calltips
        if self.CallTipActive():
            self.CallTipCancel()

        #get key info
        key         = event.GetKeyCode() #always capital letters here
        controlDown = event.CmdDown()    #use CmdDown to support mac command button and win/linux ctrl
        altDown     = event.AltDown()
        shiftDown   = event.ShiftDown()
        #currentpos  = self.GetCurrentPos()
        currentline = self.GetCurrentLine()
        #endpos      = self.GetLength()
        #selecting   = self.IsSelection()   
        
        #now check for keys
        # Return (Enter) pressed - do autoindent
        if ((key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]) and 
            (True not in [controlDown, shiftDown, altDown])):

            line=self.GetLine(currentline)
            indent = len(line)-len(line.lstrip(' ')) #find exisiting indent (all spaces no tabs)

            #find the first keyword to see whether to indent
            word=''
            for c in line[indent:]:
                if c.isalnum():
                    word = word+c
                else:
                    break
            #check for ':' don't add extra indent unless its there!
            if len(line)>2:
                has_colon = (line[-1]=='\n' and line[-2]==':') or (line[-1]==':')
            elif len(line)>1:
                has_colon = line[-1]==':'
            else:
                has_colon = False
                
            if (word in ['if','else','elif','for','while', 'def','class','try',
                        'except','finally']) and has_colon:
                indent = indent + 4
            #add indent to new line
            self.AddText('\n'+' '*indent)
        else:
            event.Skip()
