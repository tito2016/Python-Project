"""
The ConsolePage subclass for PTK engines.


Class inheritence map:
-----------------------

message_bus_MBLocalNode
            |
            |
engine.console.Console     console_frame.ConsolePage
            |                       | 
            |                       |
            engine_page.EnginePageBase
wx.STC           |              
    |            |               
engine_page.EngPageSTC          


Where:
engine.console.Console      - engine control via message bus node.
console_frame.ConsolePage   - ConsoleFrame notebook page base class
console_page.EnginePageBase - Combined EngConsole & ConsolePage
console_page.EngPageSTC     - StyledTextCtrl based EnginePageBase

"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import keyword    
import marshal
import string

import wx
from wx import stc
from wx.lib.embeddedimage import PyEmbeddedImage

from ptk_lib.engine import eng_messages
from ptk_lib.engine.console import Console

from ptk_lib.controls import dialogs
from ptk_lib.message_bus.mb_node import MBLocalNode

from ptk_lib.core_tools.fileio import FileDrop

from console_frame import ConsolePage
import console_icons
import calltip
import autocomps

#-------------------------------------------------------------------------------
#cursor navigation keys
NAVKEYS = ( wx.WXK_END  , wx.WXK_HOME,
            wx.WXK_LEFT , wx.WXK_NUMPAD_LEFT,
            wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT,
            wx.WXK_UP   , wx.WXK_NUMPAD_UP,
            wx.WXK_DOWN , wx.WXK_NUMPAD_DOWN,
            wx.WXK_PAGEDOWN, wx.WXK_PAGEUP )

#ids for popup console control menu
ID_RENAME = wx.NewId()
ID_DEBUG = wx.NewId()
ID_PROFILE = wx.NewId()

#-------------------------------------------------------------------------------
# ConsolePage base class for PTK engines
#   -   split from STC class to allow new console developement
#-------------------------------------------------------------------------------
class EnginePageBase(ConsolePage, Console):
    """
    Base class for engine consoles - containing the ConsolePage parts and engine
    control interfaces.
    """
    def __init__(self, node_name='Console.*'):
        """
        engnode = engine node name to control
        """
        #console page base class initialisation
        ConsolePage.__init__(self)
    
        #engine console base class initialisation
        app = wx.GetApp()
        Console.__init__(self, app.msg_bus, node_name)

        #Command history - cmdhistory is provided by the command history tool
        self._hist = wx.GetApp().toolmgr.get_tool('CmdHistory')
    
    #---overloaded console methods----------------------------------------------
    def manage(self):
        """
        Start controlling the engine. Returns sucess flag.
        Overloaded to update parent notebook tab with new icon/label.
        """
        res = Console.manage(self)
    
        #failed to take management of the engine
        if res is False:
            return
            
        #set page label
        n = self.Parent.GetPageIndex(self)
        self.Parent.SetPageText(n,self.englabel[-30:])

        #set page bitmap
        if self.engicon is None:
            self.engicon = console_icons.console16.GetBitmap()
        else:
            #convert icon to wxBitmap class
            self.engicon = PyEmbeddedImage(self.engicon).GetBitmap()
        n = self.Parent.GetPageIndex(self)
        self.Parent.SetPageBitmap(n, self.engicon)
        
        #register console engtasks with the engine
        self.register_task( calltip.get_call_tip)
        self.register_task( autocomps.get_autocomps_names)
        self.register_task( autocomps.get_autocomps_keys)
        self.register_task( autocomps.get_autocomps_args)
        self.register_task( autocomps.get_autocomps_path)

        return res

    def release_engine(self):
        """
        Stop managing the current engine node.
        The console will be inactive until an new engine node is set as managed.
        Returns True/False is success.

        Overloaded to update parent notebook tab with new icon/label.
        """
        res = Console.release_engine(self)
        if res is True:
            #get this pages index
            n = self.Parent.GetPageIndex(self)
            #set page label
            label = '[Disconnected] - '+self.englabel
            self.Parent.SetPageText(n,label)
            #set a dead bitmap???
        return res

    def msg_node_disconnect(self, msg):
        """
        Called when the engine message bus nodes disconnects
        Overloaded to update parent notebook tab with new icon/label.
        """
        Console.msg_node_disconnect(self, msg)

        #get this pages index
        n = self.Parent.GetPageIndex(self)
        #set page label
        label = '[Disconnected] - '+self.englabel
        self.Parent.SetPageText(n,label)
        #set a dead bitmap???

    #---Console Page methods----------------------------------------------------
    def OnPageClear(self):
        self.clear()

    def OnPageStop(self):
        """
        Called to stop/keyboard interupt this console page
        """
        self.stop()

    def OnPageSelect(self, event):
        """
        Called when the page is selected
        """
        pass

    def OnPageClose(self, event):
        """
        Called when the page is about to be closed
        """
        log.debug('In OnPageClose '+str(self.is_interactive))
        #check still managing an engine, if not close without asking
        if self.is_interactive is False:
            event.Skip()
            #disconnect from messagebus as wxpython destroys the object
            self.disconnect()
            return

        res = dialogs.ConfirmDialog('Close Engine: '+self.englabel+' ?',
                                    'Close Engine?')
        if res is False:
            event.Veto()
            return

        #release the engine from control and disconnect from the node before the
        #wx control is destroyed.
        engname = self.engine
        self.release()
        self.disconnect()
        try:
            contool = wx.GetApp().toolmgr.get_tool('Console')
            contool.close_engine(engname)
            event.Skip()
        except:
            log.exception('Error: ')

    def GetPageMenu(self):
        """
        Returns a new Settings menu object for this console.
        This should be destroyed when finished with.
        """
        menu = wx.Menu()

        #enable debugger
        dbg_item = wx.MenuItem( menu, ID_DEBUG ,'Disable debugger', 
                           'Toggle the engine debugger',wx.ITEM_NORMAL)
        bmp = console_icons.dbg_enable.GetBitmap()
        disabled_bmp = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()
        dbg_item.SetDisabledBitmap(disabled_bmp)
        if self.debug is True:
            dbg_item.SetBitmap(bmp)
            dbg_item.SetText('Disable Debugger')
        else:
            dbg_item.SetBitmap(disabled_bmp)
            dbg_item.SetText('Enable debugger')
        menu.AppendItem(dbg_item)
        menu.Bind(wx.EVT_MENU, self.OnMenuDebugger, dbg_item)
            
        #enable profiler
        pro_item = wx.MenuItem( menu, ID_PROFILE ,'Enable profiler', 
                           'Toggle the engine profiler', wx.ITEM_NORMAL)
        bmp = console_icons.engine_profile.GetBitmap()
        disabled_bmp = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()
        pro_item.SetDisabledBitmap(disabled_bmp)

        if self.profile is True:
            pro_item.SetBitmap(bmp)
            pro_item.SetText('Disable profiler')
        else:
            pro_item.SetBitmap(disabled_bmp)
            pro_item.SetText('Enable profiler')
        menu.AppendItem(pro_item)
        menu.Bind(wx.EVT_MENU, self.OnMenuProfiler, pro_item)
        menu.AppendSeparator()
        
        #Stop/Keyboard interupt
        stop_item = wx.MenuItem( menu, -1 ,"Stop    [Ctrl+C]", 
                           'Stop running code via a keyboard interrupt (Ctrl+c)',
                            wx.ITEM_NORMAL)
        stop_item.SetBitmap(console_icons.engine_stop.GetBitmap())
        menu.AppendItem(stop_item)
        menu.Bind(wx.EVT_MENU, self.OnMenuStop, stop_item)
        if self.busy is False:
            #disable the stop command
            menu.Enable(stop_item.GetId(), False)

        #Kill
        kill_item = wx.MenuItem( menu, -1 ,'Kill process', 
                           'Kill the engine process', wx.ITEM_NORMAL)
        kill_item.SetBitmap(console_icons.kill.GetBitmap())
        menu.AppendItem(kill_item)
        menu.Bind(wx.EVT_MENU, self.OnMenuKill, kill_item)
                
        menu.AppendSeparator()

        #rename engine
        name_item = wx.MenuItem( menu, ID_RENAME ,'Rename', 
                           'Rename this engine console',wx.ITEM_NORMAL)
        name_item.SetBitmap(console_icons.tab_edit.GetBitmap())

        menu.AppendItem(name_item)
        menu.Bind(wx.EVT_MENU, self.OnMenuRename, name_item)


        #disable menu items not applicable to the internal engine
        if self.engtype=='Internal':
            menu.Enable(dbg_item.GetId(), False)
            menu.Enable(pro_item.GetId(), False)
            menu.Enable(kill_item.GetId(), False)

        #disable menu items if the engine is not connected
        if self.engtype is None:
            menu.Enable(dbg_item.GetId(), False)
            menu.Enable(pro_item.GetId(), False)
            menu.Enable(stop_item.GetId(), False)
            menu.Enable(kill_item.GetId(), False)

        return menu

    #---control menu events-----------------------------------------------------
    def OnMenuRename(self, event):
        #change engine label
        dlg = wx.TextEntryDialog(None, 'Rename '+self.englabel+' to:','Rename:', self.englabel)
        if dlg.ShowModal() == wx.ID_OK:
            self.englabel = dlg.GetValue()
            #set page label
            n = self.Parent.GetPageIndex(self)
            self.Parent.SetPageText(n,self.englabel[-30:])
        dlg.Destroy()

    def OnMenuDebugger(self, event):
        #enable/disable the debugger
        debug = not self.debug
        self.enable_debug( debug )
        
        #update the menu
        menu = event.GetEventObject()
        dbg_item = menu.FindItemById(ID_DEBUG)

        bmp = console_icons.dbg_enable.GetBitmap()
        disabled_bmp = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()
        if self.debug is True:
            dbg_item.SetBitmap(bmp)
            dbg_item.SetText('Disable debugger')
        else:
            dbg_item.SetBitmap(disabled_bmp)
            dbg_item.SetText('Enable debugger')
        
    def OnMenuProfiler(self, event):
        #enable/disable the profiler
        profile = not self.profile
        self.enable_profile( profile )

        #update menu
        menu = event.GetEventObject()
        pro_item = menu.FindItemById(ID_PROFILE)

        bmp = console_icons.dbg_enable.GetBitmap()
        disabled_bmp = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()
        if self.profile is True:
            pro_item.SetBitmap(bmp)
            pro_item.SetText('Disable profiler')
        else:
            pro_item.SetBitmap(disabled_bmp)
            pro_item.SetText('Enable profiler')

    def OnMenuStop(self, event):
        self.stop()
        
    def OnMenuKill(self, event):
    
        res = dialogs.ConfirmDialog('Kill Engine: '+self.englabel+' ?',
                                    'Kill Engine?')
        if res is False:
            event.Veto()
            return
        self.kill()    

class EngPageSTC(EnginePageBase, stc.StyledTextCtrl):
    """ A console control based upon the wx.StyledTextCtrl """
    def __init__(self, parent):

        #-----------------------------------------------------------------------
        # Initalise the stc
        #-----------------------------------------------------------------------
        style=wx.CLIP_CHILDREN | wx.SUNKEN_BORDER
        stc.StyledTextCtrl.__init__(self, parent, id=-1, style=style)
        self._initSTC()         #setup stc styles

        #-----------------------------------------------------------------------
        # Internals for console functions
        #-----------------------------------------------------------------------
        #prompt position info used to get the entered line.
        self._promptpos  = 0
        self._promptline = 1
        self._promptlen = 0

        #options
        self._showlinenumbers = False
        self._showautocomps = True
        self._showcalltips = True

        #create a context menu
        self.context_menu = wx.Menu()
        self.context_menu.Append(wx.ID_CUT, "Cut")
        self.context_menu.Append(wx.ID_COPY, "Copy")
        self.context_menu.Append(wx.ID_PASTE, "Paste")
        self.context_menu.Append(wx.ID_CLEAR, "Clear")
        self.context_menu.AppendSeparator()
        self.context_menu.Append(wx.ID_SELECTALL, "Select All")

        self._initEvents()      #bind event handlers

        #create a calltip window
        self.calltip =  calltip.CallTip(self, "", pos=(-1,-1))

        #create autocomp popup window
        self.autocomp = autocomps.AutoComp(self)
        #-----------------------------------------------------------------------
        # initialise the EngPageBase class
        #-----------------------------------------------------------------------
        EnginePageBase.__init__(self)


    #---Initialisation tasks----------------------------------------------------
    def _initSTC(self):
        
        # Set the fonts
        self.faces = {
              'times': 'Courier New',
              'mono' : 'Courier New',
              'helv' : 'Courier New',
              'other': 'Courier New',
              'size' : 10,
              'backcol'   : '#FFFFFF',
              'calltipbg' : '#FFFFB8',
              'calltipfg' : '#404040'
            }

        self.SetSelForeground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        self.SetSelBackground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))

        self.SetLexer(stc.STC_LEX_PYTHON) #need to print lines longer than 64k!!!        
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        #whitespaces and tabs
        self.SetViewWhiteSpace(False)
        self.SetViewEOL(False);
        self.SetEOLMode(stc.STC_EOL_LF)

        self.SetTabWidth(4)
        self.SetUseTabs(False)
        self.SetWrapMode(True);
        self.SetEndAtLastLine(False);

        self.SetBufferedDraw(True)

        #calltip for doc string
        self.CallTipSetBackground(self.faces['calltipbg'])
        self.CallTipSetForeground(self.faces['calltipfg'])

        #disable undo/redo
        self.SetUndoCollection(False);

        #create a droptarget
        self.dt = FileDrop()
        self.SetDropTarget(self.dt)  

        #apply the options
        self.LoadOptions()

    def _initEvents(self):
        """Initialise the event handlers"""
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)#when losing window focus
        
        #update the stc when user is typing.
        self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        
        # Assign handler for the context menu and edit events
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnCMenuUpdateUI)
        self.Bind(wx.EVT_MENU, self.OnCMenuCut, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnCMenuCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnCMenuPaste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.OnCMenuSelectAll, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnCMenuClear, id=wx.ID_CLEAR)

    #---------------------------------------------------------------------------
    # overloaded engine console methods
    #---------------------------------------------------------------------------
    def clear(self):
        """
        Clear this console
        """
        self.Clear()

    def prompt(self, prompt, more=False):
        """
        Engine prompts for more user commands.
        """
        #If more is None - disable the prompt and return
        if (more is None):
            #clear the prompt if prompting
            if self.busy is False:
                self.busy = True
                self.SetSelection( self._promptpos - self._promptlen, 
                                    self.GetLength() )
                self.ReplaceSelection('')
            return 

        #get the continuation prompt
        if more is True:
            prompt = '... '

        #write the prompt
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        self.AddText(prompt)            #add the prompt
        self.EnsureCaretVisible()

        #If this is not a continuation then we want to update the prompt 
        #position to prevent previous commands/output from being edited
        if more is False:
            #update prompt position
            self._promptline = self.GetCurrentLine()
            self._promptpos = self.GetCurrentPos()

            #update the prompt length
            self._promptlen = len(prompt)
    

        #update the engine state flags
        self.busy   = False
        self.reading = False
        self.debugging = False

    def prompt_stdin(self, prompt, more=False):
        """
        Engine wants to read from the console std_in.
        """
        #disable the prompt if more is None
        if (more is None):
            #clear the prompt if prompting
            if self.reading is True:
                self.reading = False
                self.SetSelection(self._promptpos - self._promptlen, self.GetLength())
                self.ReplaceSelection('')
            return 

        #get the continuation prompt
        if more is True:
            prompt = '... '

        #write the prompt
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        self.AddText(prompt)            #add the prompt
        self.EnsureCaretVisible()

        #we only need to update the prompt position if this is a new read, this
        #is to prevent previous commands/output from being edited. 
        #If this is a continuation we can allow the previous input to be edited.
        if more is False:
            #update prompt position
            self._promptline = self.GetCurrentLine()
            self._promptpos = self.GetCurrentPos()

            #update the prompt length
            self._promptlen = len(prompt)
    
        #put the console into reading mode
        self.reading = True

    def prompt_debug(self, prompt, more=False):
        """
        Called when the debugger pauses, this method prompts for user 
        debugger commands.
        """
        #disable the debugging prompt if more is None
        if (more is None):
            #clear any prompt
            if self.debugging is True:
                self.debugging = False
                self.SetSelection( self._promptpos - self._promptlen, self.GetLength())
                self.ReplaceSelection('')
            return

        #already showing debug prompt do nothing.
        if self.debugging is True:
            return

        #get the continuation prompt
        if more is True:
            prompt = '... '

        #write the prompt
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        self.AddText(prompt)            #add the prompt
        self.EnsureCaretVisible()

        #we only need to update the prompt position if this is a new read, this
        #is to prevent previous commands/output from being edited. 
        #If this is a continuation we can allow the previous input to be edited.
        if more is False:
            #update prompt position
            self._promptline = self.GetCurrentLine()
            self._promptpos = self.GetCurrentPos()

            #update the prompt length
            self._promptlen = len(prompt)
    
        #update flags
        self.debugging = True

    def write_stdout(self, string):
        """
        Engine writes to the consoles std_out.
        """
        if self.AutoCompActive():
            self.AutoCompCancel()

        #if we are prompting or reading user input add the string before the 
        #current prompt
        if (self.busy is False) or (self.reading is True) or (self.debugging is True):
            #add the line before the current prompt 
            pos = self.PositionFromLine(self._promptline)
            #check that we are not at the beginning
            if pos==0:
                self.SetCurrentPos(pos)
                self.AddText('\n')
                self._promptpos +=1
                self._promptline+=1

            #add the text before the newline
            self.SetCurrentPos(pos-1)
            self.AddText(string)

            #update the prompt position
            slen = len(string)
            slines = string.count('\n')
            self._promptline =self._promptline+slines
            self._promptpos = self._promptpos+slen
            self.SetAnchor(self.GetLength())
            self.SetCurrentPos(self.GetLength()) #set cursor to end position
            self.EnsureCaretVisible()
            return

        #just add the text at the end.
        self.SetAnchor(self.GetLength())
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        self.AddText(string)
        self.EnsureCaretVisible()

    def write_stderr(self, string):
        """
        Engine writes to the consoles std_err.
        """
        if self.AutoCompActive():
            self.AutoCompCancel()

        #if we are prompting or reading user input add the string before the 
        #current prompt
        if (self.busy is False) or (self.reading is True) or (self.debugging is True):
            #add the line before the current prompt 
            pos = self.PositionFromLine(self._promptline)
            #check that we are not at the beginning
            if pos==0:
                self.SetCurrentPos(pos)
                self.AddText('\n')
                self._promptpos +=1
                self._promptline+=1

            #add the text before the newline
            self.SetCurrentPos(pos-1)
            self.AddText(string)

            #update the prompt position
            slen = len(string)
            slines = string.count('\n')
            self._promptline =self._promptline+slines
            self._promptpos = self._promptpos+slen
            self.SetAnchor(self.GetLength())
            self.SetCurrentPos(self.GetLength()) #set cursor to end position
            self.EnsureCaretVisible()
            return

        #just add the text at the end.
        self.SetAnchor(self.GetLength())
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        self.AddText(string)
        self.EnsureCaretVisible()

    def write_debug(self, string):
        """
        Engine writes a debugger message.
        """
        if self.AutoCompActive():
            self.AutoCompCancel()

        if string.endswith('\n') is False:
            string = string+'\n'

        #if we are prompting or reading user input add the string before the 
        #current prompt
        if (self.busy is False) or (self.reading is True) or (self.debugging is True):
            #add the line before the current prompt 
            pos = self.PositionFromLine(self._promptline)
            #check that we are not at the beginning
            if pos==0:
                self.SetCurrentPos(pos)
                self.AddText('\n')
                self._promptpos +=1
                self._promptline+=1

            #add the text before the newline
            self.SetCurrentPos(pos-1)
            self.AddText(string)

            #update the prompt position
            slen = len(string)
            slines = string.count('\n')
            self._promptline =self._promptline+slines
            self._promptpos = self._promptpos+slen
            self.SetAnchor(self.GetLength())
            self.SetCurrentPos(self.GetLength()) #set cursor to end position
            self.EnsureCaretVisible()
            return

        #just add the text at the end.
        self.SetAnchor(self.GetLength())
        self.SetCurrentPos(self.GetLength()) #set cursor to end position
        line,pos = self.GetCurLine()
        if line!='':    #add a newline before if necessary 
            self.AddText('\n')
        self.AddText(string)
        self.EnsureCaretVisible()

    def exec_source(self, source):
        """
        Execute the source as if entered at the console
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        #busy  cannnot exectute currently.
        if (self.busy is True):
            log.warning('Attempt to execute source in console when engine is busy!')
            return

        endpos = self.GetTextLength()
        self.SetSelection(self._promptpos,endpos)
        if (source.endswith('\n') is False) and (len(source.split('\n'))>1):
            source = source+'\n'
        
        text = self._AddPrompts(source, '... ')+'\n' #add extra newline for push
        self.ReplaceSelection(text)

        self.PushLine()

    def exec_file(self, filepath):
        """
        Execute the source as if entered at the console
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        #busy  cannnot exectute currently.
        if (self.busy is True):
            log.warning('Attempt to execfile in console when engine is busy!')
            return False

        endpos = self.GetTextLength()
        self.SetSelection(self._promptpos, endpos)
        source = 'execfile("'+filepath.replace('\\','\\\\')+'")'
        self.ReplaceSelection(source+'\n')
        self.PushLine()

    #---------------------------------------------------------------------------
    # Options
    #---------------------------------------------------------------------------
    def LoadOptions(self):
        """Load and apply the global console options settings"""
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Console//")

        #line numbers
        flag = cfg.ReadBool("show_linenumbers",False)
        self.SetShowLineNumbers(flag)

        #show autocomps
        flag = cfg.ReadBool("show_autocomps",True)
        self.SetShowAutoComps(flag)

        #show calltips
        flag = cfg.ReadBool("show_calltips",True)
        self.SetShowCalltips(flag)

        #use syntax highlighting
        flag = cfg.ReadBool("use_syntax_highlight",True)
        self.SetStyles(flag)

    def SetStyles(self, flag):
        faces = self.faces
        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,     "face:%(helv)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        if flag is True:

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

    def SetShowLineNumbers(self, flag):
        """Show line numbers"""
        self._showlinenumbers = flag
        if flag:
            self.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(1, 40)
        else:
            #no line numbers so set margin width
            self.SetMarginWidth(1, 0)
            self.SetMarginType(1, 0)

    def SetShowAutoComps(self, flag):
        """Automattically show autocompletes"""
        self._showautocomps = flag

    def SetShowCalltips(self, flag):
        """Automatically show calltips"""
        self._showcalltips = flag
    #---------------------------------------------------------------------------
    #  User entry methods
    #---------------------------------------------------------------------------
    def PushLine(self):
        """ Push an entered line to the engine"""
        if self.connected is False:
            log.warning('Attempt to push line to engine when disconnected!')
            return

        #reset history search/position when the line is changed.
        self._hist.SetSearchString()

        #get the line from the stc
        endpos = self.GetLength()
        line = self.GetTextRange(self._promptpos,endpos)

        #1) console is reading from StdIn
        if self.reading:
            #unset flag
            self.reading = False
            #strip continuation prompts
            line = self._StripPrompts(line,'... ')
            # In case the command is unicode try encoding it
            if type(line) == unicode:
                try:
                    line = line.encode(wx.GetDefaultPyEncoding())
                except UnicodeEncodeError:
                    pass # otherwise leave it alone

            #send the line to the engine
            self.push(line)
            return

        #2) console is debugging
        if self.debugging:
            #unset the flag
            self.debugging = False
            #strip continuation prompts
            line = self._StripPrompts(line, '... ')
            # In case the command is unicode try encoding it
            if type(line) == unicode:
                try:
                    line = line.encode(wx.GetDefaultPyEncoding())
                except UnicodeEncodeError:
                    pass # otherwise leave it alone

            #send the line to the engine
            self.push(line)
            return

        #3) Prompting for command
        else:
            self.busy = True #this will be unset by the next call to Prompt
            #strip any continuation prompts from the line
            line = self._StripPrompts(line, '... ')

            #send line to engine - the engine will process this line and send a 
            #message to: 
            #   prompt if a new command is needed.
            #   read_stdin if input from the user is needed.
            #   write_stdout to display output
            #   write_stderr to display errors
            self.push(line)
            return

    def _AddPrompts(self, line, prompt):
        """Adds continuation prompts to a multiline command"""
        line=line.replace('\n','\n'+prompt)
        return line

    def _StripPrompts(self, line, prompt):
        """Remove continuation prompts from a multiline command"""
        line = line.replace('\n'+prompt, '\n')
        return line    
    #---------------------------------------------------------------------------
    # overloaded stc methods
    #---------------------------------------------------------------------------
    def Cut(self):
        """Remove selection and place it on the clipboard."""
        if self.CanEdit() is True:
            if self.AutoCompActive():
                self.AutoCompCancel()
            if self.CallTipActive():
                self.CallTipCancel()
            stc.StyledTextCtrl.Cut(self)
            #reset history search/position when the line is changed.
            self._hist.SetSearchString()
        else:
            #line = self.GetSelectedText()
            #line = self._StripPrompts(line,'... ')
            #data = wx.TextDataObject(line)
            #print line,data
            #self._clip(data)
            stc.StyledTextCtrl.Copy(self)
            self.Copy()

    def Copy(self):
        line = self.GetSelectedText()
        line = self._StripPrompts(line,'... ')
        data = wx.TextDataObject(line)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(data)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")    
    
    def Paste(self):
        if self.CanEdit() is True:
            #close autocomps and call tip
            if self.AutoCompActive():
                self.AutoCompCancel()
            if self.CallTipActive():
                self.CallTipCancel()

            #get the current pos, paste the text then insert prompts
            startpos = self.GetCurrentPos()
            stc.StyledTextCtrl.Paste(self)
            endpos = self.GetLength()
            line = self.GetTextRange(startpos,endpos)
            
            #first strip any prompts
            line = self._StripPrompts(line,'... ')

            #add continuation prompts back in if needed
            line = self._AddPrompts(line,'... ')

            #put line into stc
            self.SetSelection(startpos, endpos)
            self.ReplaceSelection(line)
            #reset history search/position when the line is changed.
            self._hist.SetSearchString()

    def Clear(self):
        """
        Clear this console
        """
        #do nothing if not connected
        if self.connected is False:
            return
            
        if self.AutoCompActive():
            self.AutoCompCancel()
        if self.CallTipActive():
            self.CallTipCancel()

        #prompting so clear all but the current line.
        if (self.busy is False) or (self.reading is True) or (self.debugging is True):
            #get the current prompt
            startpos = self.PositionFromLine(self._promptline)
            prompt = self.GetTextRange(startpos,self._promptpos)
            #get the current line
            endpos = self.GetLength()
            line = self.GetTextRange(self._promptpos,endpos)
            #clear the control and add the prompt and line
            self.ClearAll()
            self.AddText(prompt)
            self._promptline = self.GetCurrentLine()
            self._promptpos = self.GetCurrentPos()
            self.AddText(line)
        else:
            self.ClearAll()

    def ClearCommand(self):
        """Clears the current command"""
        if (self.busy is True) and ((self.reading is False) or (self.debugging is False)):
            return

        #check engine is still connected
        if self.connected is False:
            log.warning('Attempt to clear command when engine is disconnected!')
            return

        endpos = self.GetTextLength()
        self.SetSelection(self._promptpos, endpos)
        self.ReplaceSelection('')
        #reset history search/position when the line is changed.
        self._hist.SetSearchString()

    def GetCommand(self):
        """
        Returns the current command line being edited i.e. from prompt to the 
        current cursor position. To get the complete line ensure cursors is set
        to the end.
        """
        curpos  = self.GetCurrentPos()
        line = self.GetTextRange(self._promptpos, curpos)
        return line
        
    #---Command history---------------------------------------------------------
    def CmdHist_ReplacePrevious(self):
        """Move to previous command in command history"""
        #if busy (and not debugging and paused) do nothing
        if self.busy and  not (self.debugger.paused):
            return
        
        #check engine is connected
        if self.connected is False:
            return

        #set the search string to the current line contents if not already in 
        # the history.
        if self._hist.GetPosition()==-1:
            endpos = self.GetTextLength()
            searchstr = self.GetTextRange(self._promptpos,endpos)
            searchstr = self._StripPrompts(searchstr, '... ')
            self._hist.SetSearchString(searchstr)

        #get the previous matching command
        cmd = self._hist.GetPreviousCommand()

        #replace text
        endpos = self.GetTextLength()
        self.SetSelection(self._promptpos,endpos)
        cmd = self._AddPrompts(cmd, '... ')
        self.ReplaceSelection(cmd)

    def CmdHist_ReplaceNext(self):
        """Move to next command in command history """
        #if busy (and not debugging and paused) do nothing
        if self.busy and  not (self.debugger.paused):
            return

        #check engine is connected
        if self.connected is False:
            return

        #set the search string to the current line contents if not already in 
        # the history.
        if self._hist.GetPosition()==-1:
            endpos = self.GetTextLength()
            searchstr = self.GetTextRange(self._promptpos,endpos)
            searchstr = self._StripPrompts(searchstr, '... ')
            self._hist.SetSearchString(searchstr)

        #get the previous matching command
        cmd = self._hist.GetNextCommand()
        
        #replace text
        endpos = self.GetTextLength()
        self.SetSelection(self._promptpos,endpos)
        cmd = self._AddPrompts(cmd, '... ')
        self.ReplaceSelection(cmd)

    def CmdHist_Clear(self):
        """Clears the command history"""
        self._hist.Clear()

    #---Autocompletes/Calltips--------------------------------------------------
    def OpenAutoComplete(self):
        """Open the autocomplete list"""
        #if busy (and not debugging and paused) do nothing
        if self.busy and  not (self.debugger.paused):
            return
            
        #close calltip if open
        if self.CallTipActive():
            self.CallTipCancel()
            
        #check engine is still connected
        if self.connected is False:
            log.warning('Attempt to open autocomps when engine is disconnected!')
            return

        # check if the current position is beyond the current prompt
        currentpos = self.GetCurrentPos()
        if  currentpos < self._promptpos:
            return

        #get the current line(s) - from prompt to current position
        line = self.GetCommand()   
            
        #find autocomps and show
        self.autocomp.ShowAutoComps(line)
    
    def AutoCompActive(self):
        return self.autocomp.IsShown()
        
    def AutoCompCancel(self):
        return self.autocomp.Cancel()

    def OpenCallTip(self):
        """Opens the calltip"""
        #if busy (and not debugging and paused) do nothing
        if self.busy and  not (self.debugger.paused):
            return
        
        #close autocomp if open
        if self.AutoCompActive():
            self.AutoCompCancel()
        
        #check engine is still connected
        if self.connected is False:
            log.warning('Attempt to open calltip when engine is disconnected!')
            return

        #check if the current position is beyond the current prompt
        currentpos = self.GetCurrentPos()
        if  currentpos < self._promptpos:
            return

        #get the current line(s) - from prompt to current position
        line = self.GetCommand()   
        self.calltip.ShowCallTip(line)

    def CallTipActive(self):
        return self.calltip.IsShown()

    def CallTipCancel(self):
        self.calltip.Hide()

    #---helper methods----------------------------------------------------------
    def CanEdit(self):
        """Return true if editing should succeed."""
        # check user input is allowed;
        if (self.busy is True) and (self.reading is False) and (self.debugging is False):
            return False

        #check engine is still connected
        if self.connected is False:
            return

        # check if the current position is beyond the current prompt
        currentpos = self.GetCurrentPos()
        if  currentpos < self._promptpos:
            return False

        # check that if text is selected that it does not extend beyond prompt
        if (self.GetSelectionStart()<self._promptpos):
            return False
        if (self.GetSelectionEnd()<self._promptpos):
            return False
        return True

    def IsSelection(self):
        """Returns true if text is selected"""
        result = self.GetSelectionStart() != self.GetSelectionEnd()
        return result

    #---------------------------------------------------------------------------
    # Event handlers
    #---------------------------------------------------------------------------
    def OnKeyDown(self, event):
        """Key down event handler."""
    
        #close any open calltips
        if self.CallTipActive():
            self.CallTipCancel()

        #get key info
        key         = event.GetKeyCode() #always capital letters here
        controlDown = event.CmdDown()    #use CmdDown to support mac command button and win/linux ctrl
        altDown     = event.AltDown()
        shiftDown   = event.ShiftDown()
        currentpos  = self.GetCurrentPos()
        currentline = self.GetCurrentLine()
        endpos      = self.GetLength()
        selecting   = self.IsSelection()   
        edit        = self.CanEdit() #check if we can edit

        #print key, controlDown
        
        #now check for keys
        # Return (Enter) pressed - Process the line
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            #check on which line the key was pressed
            if edit is False:
                #key pressed in non-editable region move to endpos
                self.SetAnchor(endpos)
                self.SetCurrentPos(endpos)
                return

            elif controlDown is True: #only use ctrl-enter for multiline commands? or currentpos !=endpos:
                #ctrl+enter pressed or not at the end so insert a new line and
                #prompt
                self.AddText('\n... ')
                return

            else:#enter pressed on last line process it.
                #move to the end of the line and add \n
                self.SetAnchor(endpos)
                self.SetCurrentPos(endpos)
                self.AddText('\n')
                self.PushLine()
                return
        
        #Cut / Copy /Paste using insert/delete do not result in char events so
        # check for them here
        elif (shiftDown and key == wx.WXK_DELETE):
            self.Cut()

        elif controlDown and not shiftDown and key==wx.WXK_INSERT:
            self.Copy() 

        elif (shiftDown and not controlDown and key == wx.WXK_INSERT):
            self.Paste()
            
        #Cut/Copy (or keyboard interrupt)/paste using ctrl+x,c,v       
        elif (controlDown and key==ord('X')):
            self.Cut()

        # Control + c can be copy or keyboard interupt depending on the engine state
        elif (controlDown and key==ord('C')):
            if selecting:
                #copy selection
                self.Copy()
            elif self.busy:
                # stop running command via keyboard interrupt
                self.stop()
            
        elif (controlDown and key==ord('V')):
            self.Paste()
        
        # Command history keys
        elif (controlDown and key in [wx.WXK_UP,wx.WXK_NUMPAD_UP] ):
            self.CmdHist_ReplacePrevious()

        elif (controlDown and key in [wx.WXK_DOWN,wx.WXK_NUMPAD_DOWN]):
            self.CmdHist_ReplaceNext()

        # Clear the current, unexecuted command.
        elif(key==wx.WXK_ESCAPE):
            self.ClearCommand()

        # manually invoke AutoComplete
        elif controlDown and key == wx.WXK_SPACE:
            self.OpenAutoComplete()

        # manually invoke calltip - ctrl+? ctrl+/
        elif controlDown and (key==47):
            self.OpenCallTip()
            
        # backspace
        elif key == wx.WXK_BACK:
            if (currentpos>(self._promptpos)):
                event.Skip()

        # Don't toggle between insert mode and overwrite mode.
        elif key == wx.WXK_INSERT:
            pass

        #catch the home key and shift down
        elif edit is True and key == wx.WXK_HOME:
            if shiftDown is True:
                self.SetAnchor(currentpos)
            else:
                self.SetAnchor(self._promptpos)
            self.SetCurrentPos(self._promptpos)

        #Allow navigation in uneditable regions
        elif edit is False and key in NAVKEYS: 
            event.Skip()

        #in uneditable region skip event
        elif (edit is False) and ( unichr(key) in string.printable):
                endpos = self.GetLength()
                self.SetAnchor(endpos)
                self.SetCurrentPos(endpos)
                self.EnsureCaretVisible()
                event.Skip() #skip to ensure char gets added by stc
            
        #key press was not caught, so pass it on to the stc...
        elif edit==True:
            event.Skip(); #allow the stc to process the key if ok to edit
        

    def OnChar(self, event):
        """handles single keypresses - only recieves an event if onKeyDown skips"""
        #get key
        key = event.GetUnicodeKey()
        char = unichr(key)

        #autocompletes
        if (char=='.'):
            self.AddText('.')
            if self._showautocomps is True:
                self.OpenAutoComplete()
               
        #call tip
        elif (char=='('):
            self.AddText('(')
            if self._showcalltips is True:
                self.OpenCallTip()
            
        #catch stray '\r' on windows? not on gtk
        elif key==13: 
            pass
        
        else:
            #reset history search/position when the line is changed.
            self._hist.SetSearchString()
            event.Skip()

    def OnKillFocus(self, event):
        """Close any popups when focus is lost"""
        if self.AutoCompActive():
            self.AutoCompCancel()
        if self.CallTipActive():
            self.CallTipCancel()
        event.Skip()

    def OnUpdateUI(self, event):
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

        event.Skip()



    #Context menu events
    def OnContextMenu(self, evt):
        """Create and display a context menu for the shell"""
        self.PopupMenu(self.context_menu)
        
    def OnCMenuUpdateUI(self, evt):
        """disable the context menu actions that are not possible"""
        id = evt.Id
        if id == wx.ID_CUT:
            evt.Enable(self.CanEdit() and self.IsSelection())
        elif id == wx.ID_COPY:
            evt.Enable(self.IsSelection())
        elif id == wx.ID_PASTE:
            evt.Enable(self.CanEdit() and self.CanPaste())

       
    # context menu events
    def OnCMenuCut(self,evt):
        """Cut event handler"""
        self.Cut()

    def OnCMenuCopy(self,evt):
        """Copy event handler"""
        self.Copy()

    def OnCMenuPaste(self,evt):
        """Paste event handler"""
        self.Paste()

    def OnCMenuClear(self,evt):
        """Clear event handler"""
        self.Clear()

    def OnCMenuSelectAll(self,evt):
        """Select all menu handler"""
        self.SelectAll()
    
