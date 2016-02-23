"""
Inspector Control

InspectorControl - the main panel class
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import keyword                  

import wx
import wx.stc                       

from ptk_lib.controls import infoctrl
from ptk_lib.controls import toolpanel
from ptk_lib.resources import ptk_icons,common16

from ptk_lib.core_tools.fileio import FileDrop
from ptk_lib.core_tools.console import AddressCtrl, EVT_ENGINE_ADDRESS
from ptk_lib.core_tools.editor import editor_icons

import inspector_tasks

#---The control-----------------------------------------------------------------
class InspectorControl(wx.Panel):
    def __init__(self,parent, tool):
        """Create a Inspector panel"""
        wx.Panel.__init__(self, parent, id=-1, size=(200, 100))
        #store reference to the parent tool.
        self.tool = tool

        #get references to the Console and NSBrowser tools
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')
        self.nsbtool = app.toolmgr.get_tool('NSBrowser')

        #The current object
        self.data = {}

        #Create a sizer
        vbox = wx.BoxSizer(wx.VERTICAL)
        self._CreateTools()
        vbox.Add(self.tools, 0, wx.EXPAND)
        self.info=infoctrl.InfoCtrl(self,-1)
        vbox.Add(self.info, 1, wx.EXPAND, 0)
        self.SetSizer(vbox)

        #create a droptarget
        self.dt = FileDrop()
        self.SetDropTarget(self.dt)  

        #set address to starting string
        self._InspectNone()

    def _CreateTools(self):
        """Creates the toolbar panel"""
        self.tools = toolpanel.ToolPanel(self,-1)
        #set the status bar
        self.tools.SetStatusBar(self.console.frame.StatusBar)

        #set the icon size
        self.tools.SetToolBitmapSize((16,16))

        refresh_bmp = common16.view_refresh.GetBitmap()
        up_bmp      = common16.go_up.GetBitmap()

        #address bar
        self.tools.AddStaticLabel('Current object: ')
        self.addbar = AddressCtrl(self.tools,-1,self.tool.msg_node,size=(150,-1))
        self.tools.AddControl(self.addbar)
        self.addbar.Bind(EVT_ENGINE_ADDRESS, self.OnAddress)

        #refresh
        id = wx.NewId()
        self.tools.AddTool(id, refresh_bmp, wx.ITEM_NORMAL,
                            shortHelp='Refresh the object info',
                            longHelp='Refresh the object info')
        self.Bind(wx.EVT_TOOL, self.OnRefresh ,id=id)

        #up a level
        id = wx.NewId()
        self.tools.AddTool(id, up_bmp, wx.ITEM_NORMAL,
                            shortHelp='Move up a namespace level',
                            longHelp='Move up a namespace level')
        self.Bind(wx.EVT_TOOL, self.OnUp ,id=id)

    #---interface methods-------------------------------------------------------
    def GetAddress(self, engname=None):
        """Get the current object address (if engname is given the address from 
        the memory is returned)"""
        return self.addbar.GetAddress()

    def SetAddress(self,newadd, engname=None):
        """Set the current object address (if engname is given the address in 
        the memory is set)"""
        self.addbar.SetAddress(newadd, engname)

    def RefreshAddress(self):
        """Update the the inspector view"""
        self.addbar.RefreshAddress()

    def AcceptsFocus(self):
        return True

    def Inspect(self,engname,oname):
        """Display the info for the object given by oname in the current engine"""
        log.debug('in inspect: '+str(oname))
        #get the engine interface
        if engname is None:
            eng = None
        else:
            eng = self.console.get_engine_console(engname)

        #check it
        if eng is None:
            self._InspectNone()
            return
        #check for toplevel address.
        if oname=='':
            self._InspectTip()
            return

        #check if the inspector engine tasks are regitered if not registered all
        # of them
        if 'get_object_category' not in eng.get_registered_tasks():
            eng.register_task(inspector_tasks.get_object_category)
            eng.register_task(inspector_tasks.get_type_info)
            eng.register_task(inspector_tasks.get_routine_info)
            eng.register_task(inspector_tasks.get_module_info)
            eng.register_task(inspector_tasks.get_instance_info)

        #get the object category (type,routine,module,instance)
        cat = eng.run_task('get_object_category',(oname,))

        #check object category and update infoctrl
        if cat == 'type':
            self.data = eng.run_task('get_type_info',(oname,))
            if self.data !=None:
                self._InspectType()
        elif cat == 'routine':
            self.data = eng.run_task('get_routine_info',(oname,))
            if self.data !=None:
                self._InspectRoutine()
        elif cat == 'module':
            self.data = eng.run_task('get_module_info',(oname,))
            if self.data !=None:
                self._InspectModule()
        else:
            self.data = eng.run_task('get_instance_info',(oname,))
            self._InspectInstance(oname,eng)

    def _InspectNone(self):
        """No engine - clear and disable"""
        self.data = {}
        self.info.ClearItems()
        label = "Tip:"
        value = "Start a python engine using the engine toolbar (icon to the right of the current engine list). Objects in the engine can then be inspected here."
        bmp = common16.dialog_information.GetBitmap() # info icon.
        self.info.AddItem(label, value, bitmap=bmp, orient=wx.VERTICAL, 
                            style=infoctrl.ITEM_STATIC, fill=False)
        self.Disable()

    def _InspectTip(self):
        """Toplevel show tip"""
        self.data = {}
        self.info.Freeze()
        self.info.ClearItems()
        label = "Tip:"
        value = "Enter an object, select 'inspect' in the namespace browser context menu or type inspect(name) to display information about an object"
        bmp = common16.dialog_information.GetBitmap() # info icon.
        self.info.AddItem(label, value, bitmap=bmp, orient=wx.VERTICAL, 
                            style=infoctrl.ITEM_STATIC, fill=False)
        self.info.Thaw()

    def _InspectType(self):
        self.info.Freeze()
        self.info.ClearItems()
        #type (module.type)
        label = self.data['type_name'] +':'
        value = self.data['obj_name']
        icon = self.nsbtool.get_type_icon(self.data['obj_name'])
        if icon is None:
            icon = self.nsbtool.get_type_icon(self.data['type_module']+'.'+self.data['type_name'])
        if icon is None:
            log.warning('cannot find icon for type? :'+self.data['type_module']+'.'+self.data['type'])
            icon = self.nsbtool.get_type_icon('__builtin__.type')
        bmp = wx.BitmapFromIcon(icon)
        self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_STATIC, fill=False)
        #doc
        label = "Docstring:"
        value = wx.TextCtrl(self,-1,self.data['doc'],style=wx.NO_BORDER|wx.TE_READONLY|wx.TE_MULTILINE)
        self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)

        #conargspec
        label = "Constructor args:"
        value = self.data['conargspec']
        self.info.AddItem(label, value, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_NOICON, fill=False)

        #condoc
        label = "Constructor Docstring:"
        value = wx.TextCtrl(self,-1,self.data['condoc'],style=wx.NO_BORDER|wx.TE_READONLY|wx.TE_MULTILINE)
        self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)

        #sourcefile
        bmp = editor_icons.editor16.GetBitmap()
        label = "Source file:"
        value = self.data['sourcefile']
        if value is None:
            value='Not available.'
        item = self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_BUTTON, fill=False)
        item.Bind(infoctrl.EVT_ICON_CLICK, self.OnFile)
        item.SetToolTipString('Open in editor')

        #source
        label = "Source:"
        value = ReadOnlyPythonSTC(self,-1)
        value.SetText(self.data['source'])
        item = self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)
        item.Expand(False)

        self.info.Thaw()

    def _InspectRoutine(self):
        self.info.Freeze()
        self.info.ClearItems()
        #type (module.type)
        label = self.data['type_name'] +':'
        value = self.data['obj_name']
        icon = self.nsbtool.get_type_icon(self.data['type'])
        if icon is None:
            style = infoctrl.ITEM_NOICON
            bmp = None
        else:
            style = infoctrl.ITEM_STATIC
            bmp = wx.BitmapFromIcon(icon)
            
        self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=style, fill=False)

        #argspec
        label = "Arguments:"
        value = self.data['argspec']
        self.info.AddItem(label, value, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_NOICON, fill=False)

        #doc
        label = "Docstring:"
        value = wx.TextCtrl(self,-1,self.data['doc'],style=wx.NO_BORDER|wx.TE_READONLY|wx.TE_MULTILINE)
        item = self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)
        
        #sourcefile
        bmp = editor_icons.editor16.GetBitmap()
        label = "Source file:"
        value = self.data['sourcefile']
        if value is None:
            value = 'Not available.'
        item = self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_BUTTON, fill=False)
        item.Bind(infoctrl.EVT_ICON_CLICK, self.OnFile)
        item.SetToolTipString('Open in editor')

        #source
        label = "Source:"
        value = ReadOnlyPythonSTC(self,-1)
        value.SetText(self.data['source'])
        item = self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)
        item.Expand(False)

        self.info.Thaw()

    def _InspectModule(self):
        self.info.Freeze()
        self.info.ClearItems()
        label = 'Module:'
        value = self.data['obj_name']
        icon = self.nsbtool.get_type_icon('__builtin__.module')
        if icon is None:
            style = infoctrl.ITEM_NOICON
            bmp = None
        else:
            style = infoctrl.ITEM_STATIC
            bmp = wx.BitmapFromIcon(icon)
            
        self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=style, fill=False)

        #doc
        label = "Docstring:"
        value = wx.TextCtrl(self,-1,self.data['doc'],style=wx.NO_BORDER|wx.TE_READONLY|wx.TE_MULTILINE)
        self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)
        
        #sourcefile
        bmp = editor_icons.editor16.GetBitmap()
        label = "Source file:"
        value = self.data['sourcefile']
        if value is None:
            value = 'Not available.'
        item = self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=infoctrl.ITEM_BUTTON, fill=False)
        item.Bind(infoctrl.EVT_ICON_CLICK, self.OnFile)
        item.SetToolTipString('Open in editor')

        #source
        label = "Source:"
        value = ReadOnlyPythonSTC(self,-1)
        value.SetText(self.data['source'])
        item = self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)
        item.Expand(False)

        self.info.Thaw()

    def _InspectInstance(self,oname,eng):
        self.info.Freeze()
        self.info.ClearItems()
        #type (module.type)
        label = 'Type:'
        value = self.data['type']
        icon = self.nsbtool.get_type_icon(self.data['type'])
        if icon is None:
            icon = self.nsbtool.get_type_icon(-1)
        bmp = wx.BitmapFromIcon(icon)
        style = infoctrl.ITEM_BUTTON
        item = self.info.AddItem(label, value, bitmap=bmp, orient=wx.HORIZONTAL, 
                            style=style, fill=False)
        item.SetToolTipString('Click to inpsect type')
        item.Bind(infoctrl.EVT_ICON_CLICK, self.OnInspectType)

        #get the type info/value from nsbrowser
        infocall = self.nsbtool.get_type_info(self.data['type'])
        if infocall is None:
            infocall = self.nsbtool.get_type_info(-1)
        info = infocall(eng, oname)
        label = 'Info/Value:'
        style = infoctrl.ITEM_COLLAPSE
        value = wx.TextCtrl(self,-1,info,style=wx.NO_BORDER|wx.TE_READONLY|wx.TE_MULTILINE)
        self.info.AddItem(label, value, style=infoctrl.ITEM_COLLAPSE, fill=True)

        self.info.Thaw()

    #---event handlers----------------------------------------------------------
    def OnAddress(self,event):
        """change to new object that was entered in the address bar"""
        if event.address is not None:
            self.Enable()
            self.Inspect(event.engname,event.address)

    def OnRefresh(self,event):
        new = self.GetAddress()
        self.SetAddress(new)

    def OnFile(self,event):
        file = self.data.get('sourcefile',None)
        if file is not None:
            self.tool.msg_node.send_msg('FileIO','Open', (file,))

    def OnInspectType(self,event):
        new = self.GetAddress() + '.__class__'
        self.SetAddress(new)

    def OnUp(self,event):
        """Move up a level"""
        self.addbar.MoveUpLevel()


#---stc control for code--------------------------------------------------------
class ReadOnlyPythonSTC(wx.stc.StyledTextCtrl):
    def __init__(self, parent, id):
        wx.stc.StyledTextCtrl.__init__(self, parent, id)

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
        self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=wx.ID_SELECTALL)

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
        menu.Append(wx.ID_COPY, "Copy")
        menu.AppendSeparator()
        menu.Append(wx.ID_SELECTALL, "Select All")
        self.PopupMenu(menu)

    def OnCopy(self,evt):
        self.Copy()

    def OnSelectAll(self,evt):
        self.SelectAll()
