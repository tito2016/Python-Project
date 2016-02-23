#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

import wx
from wx.lib.embeddedimage import PyEmbeddedImage
import wx.aui as aui #for notebook

from ptk_lib.resources import common16, debugger16, common22, debugger22
from ptk_lib.controls import controls
from ptk_lib.controls import aui_addons
from ptk_lib.controls import toolpanel

from ptk_lib.message_bus import mb_protocol
from ptk_lib.engine import eng_messages
from ptk_lib.core_tools.console import console_messages

import editor_icons
import editor_messages

#---IDS-------------------------------------------------------------------------
ID_DEBUG = wx.NewId()
ID_PAUSE = wx.NewId()
ID_END = wx.NewId()
ID_STEP = wx.NewId()
ID_STEPIN = wx.NewId()
ID_STEPOUT = wx.NewId()
ID_BPLIST = wx.NewId()
ID_STOP = wx.NewId()

#---debugger toolbar for console window-----------------------------------------
class DebugConsoleTools(toolpanel.ToolPanel):
    def __init__(self, parent, tool):

        toolpanel.ToolPanel.__init__(self,parent,-1)

        #store a reference to the Console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #store a reference to the editor tool
        self.tool = tool

        #set the icon size
        self.SetToolBitmapSize((16,16))
        
        #set the status bar to use
        self.SetStatusBar(self.console.frame.StatusBar)

        #load some icons
        bmp_enable   = debugger16.dbg_toggle.GetBitmap()
        bmp_pause    = debugger16.dbg_pause.GetBitmap() 
        bmp_end      = debugger16.dbg_end.GetBitmap()
        bmp_step     = debugger16.dbg_step.GetBitmap()
        bmp_stepin   = debugger16.dbg_step_in.GetBitmap()
        bmp_stepout  = debugger16.dbg_step_out.GetBitmap()
        bmp_bplist   = debugger16.dbg_bp_list.GetBitmap()

        #----------------------------------------------------------------------- 
        #enable disable debugger toggle button
        self.AddTool(ID_DEBUG, bmp_enable, wx.ITEM_CHECK,
                "Enable engine debugger", 
                "Enable the engine debugger mode")
        self.Bind(wx.EVT_TOOL, self.OnDebug, id=ID_DEBUG)

        self.AddSeparator()

        #-----------------------------------------------------------------------
        #pause/resume
        self._paused = False
        self.AddTool( ID_PAUSE, bmp_pause, wx.ITEM_CHECK,
                        'Pause code execution',
                        'Pause code execution')
        self.Bind(wx.EVT_TOOL, self.OnPause, id=ID_PAUSE)

        #end debugging
        self.AddTool( ID_END, bmp_end, wx.ITEM_NORMAL,
                        'End debugging',
                        'End debugging and finish running command')
        self.Bind(wx.EVT_TOOL, self.OnEnd, id=ID_END)

        self.AddSeparator()

        #step
        self.AddTool( ID_STEP, bmp_step, wx.ITEM_NORMAL,
                        'Step to next line', 
                        'Step to next line of running command')
        self.Bind(wx.EVT_TOOL, self.OnStep, id=ID_STEP)

        #step in
        self.AddTool( ID_STEPIN, bmp_stepin, wx.ITEM_NORMAL,
                        'Step into the new scope',
                        'Step into the new scope')
        self.Bind(wx.EVT_TOOL, self.OnStepIn, id=ID_STEPIN)

        #step out
        self.AddTool( ID_STEPOUT, bmp_stepout, wx.ITEM_NORMAL,
                        'Step out of the current scope', 
                        'Step out of the current scope')
        self.Bind(wx.EVT_TOOL, self.OnStepOut, id=ID_STEPOUT)

        self.AddSeparator()

        #breakpoints pane
        self.AddTool( ID_BPLIST, bmp_bplist, wx.ITEM_CHECK,
                        'Show/Hide breakpoint pane',
                        'Show/Hide breakpoint pane')
        self.Bind(wx.EVT_TOOL, self.OnBPPane, id=ID_BPLIST)

        #bind to the break_point pane events to update the toggle button
        # when shown/hidden
        bp_pane = self.tool.console_pane
        bp_pane.window.Bind( wx.EVT_SHOW, self.OnBPShow)
        self.AddSeparator()

        #scope list
        self.AddStaticLabel( 'Debugger stack: ')
        self.scopelist = wx.Choice(self, -1, size=(150, -1), choices=['Main'])
        self.AddControl(self.scopelist)
        #self.scopelist.SetMaxSize((-1,20))
        self.Bind(wx.EVT_CHOICE, self.OnScopeChoice, self.scopelist)

        self.Realize()

        #subscribe to engine/console tool messages
        self.tool.msg_node.subscribe( console_messages.CONSOLE_SWITCHED, 
                                        self.msg_console)
        self.tool.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                        self.msg_console) 
        self.tool.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine',
                                        self.msg_console) 

        self.tool.msg_node.subscribe( eng_messages.ENGINE_STATE_BUSY, 
                                        self.msg_engine)
        self.tool.msg_node.subscribe( eng_messages.ENGINE_STATE_DONE, 
                                        self.msg_engine)
        self.tool.msg_node.subscribe( eng_messages.ENGINE_DEBUG, 
                                        self.msg_engine)

    #---messages----------------------------------------------------------------
    def msg_engine(self, msg):
        """
        Message handler for engine messages:
            ENGINE_BUSY
            ENGINE_DONE
            ENGINE_DEBUG* published messages
        """
        engname = msg.get_from()
        if self.console.is_engine_current(engname) is False:
            return
        self._update_tools()

    def msg_console(self,msg):
        """
        Message handler for console tool messages: 
            CONSOLE_SWITCHED
            CONSOLE_ENGINE_CONNECTED
        """
        self._update_tools()

    def _update_tools(self):
        """
        Update the tools state.
        """
        #get the engine console
        eng = self.console.get_current_engine()

        #no engine/not an engine
        if eng is None:
            self.EnableTool(ID_DEBUG, False)
            self.ToggleTool(ID_DEBUG, False)
            self.EnableTool(ID_PAUSE, False)
            self.ToggleTool(ID_PAUSE, False)
            self.EnableTool(ID_END, False)
            self.EnableTool(ID_STEP  , False)            
            self.EnableTool(ID_STEPIN  , False)
            self.EnableTool(ID_STEPOUT  , False)
            self.scopelist.Enable(False)
            return

        #is an engine update the tool state
        busy, debug, profile = eng.get_state()
        paused, can_stepin, can_stepout = eng.debugger.get_state()

        #debug button
        self.EnableTool(ID_DEBUG, True)
        self.ToggleTool(ID_DEBUG , debug)

        #paused button
        self.EnableTool(ID_PAUSE, debug)
        self.ToggleTool(ID_PAUSE, paused)
        self.EnableTool(ID_END, (busy and debug))

        if paused is True:
            self.SetToolShortHelp(ID_PAUSE,'Resume running command')
            self.SetToolLongHelp(ID_PAUSE,'Resume running command')
        else:
            self.SetToolShortHelp(ID_PAUSE,'Pause running command')
            self.SetToolLongHelp(ID_PAUSE,'Pause running command')

        #steps
        self.EnableTool(ID_STEP  , (paused and busy))            
        self.EnableTool(ID_STEPIN  , can_stepin)
        self.EnableTool(ID_STEPOUT  , can_stepout)

        #scopelist
        self.scopelist.Enable((paused and busy))
        self.scopelist.SetItems( eng.debugger.get_scopelist() )
        self.scopelist.SetSelection( eng.debugger.get_active_scope() )

        self.Refresh()

    #---events------------------------------------------------------------------
    def OnDebug(self, event):
        """Enable engine debugger"""
        flag = event.IsChecked()
        eng = self.console.get_current_engine()
        if eng is None:
            return
        res = eng.enable_debug(flag)

    def OnPause(self,event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        #check if we are pausing or resumeing
        if eng.debugger.paused :
            res = eng.debugger.resume()
            res = not res
        else:
            res = eng.debugger.pause()

    def OnEnd(self,event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.end()

    def OnStep(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step()
    
    def OnStepIn(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step_in()

    def OnStepOut(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step_out()

    def OnBPPane(self, event):
        #show/hide the breakpoint pane
        if self.tool.console_pane.IsShown():
            self.tool.console_pane.Hide()
            self.ToggleTool(ID_BPLIST, False)
            self.Refresh()
        else:
            self.tool.console_pane.Show()
            self.ToggleTool(ID_BPLIST, True)
            self.Refresh()
        self.Parent.auimgr.Update()

    def OnBPShow(self, event):
        #The breakpoint pane has been shown/hidden
        shown = event.GetShow()
        self.ToggleTool(ID_BPLIST, shown)
        self.Refresh()
        event.Skip()

    def OnScopeChoice(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        level = self.scopelist.GetSelection()
        eng.debugger.set_active_scope(level)

#---debugger toolbar for editor-------------------------------------------------
class DebugEditorTools(toolpanel.ToolPanel):
    def __init__(self, parent, tool):
        toolpanel.ToolPanel.__init__(self,parent,-1)

        #store a reference to the Console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #store a reference to the editor tool
        self.tool = tool
        
        #set the icon size
        self.SetToolBitmapSize( (22,22) )
        
        #set the status bar to use
        self.SetStatusBar(parent.StatusBar)

        #load some icons
        bmp_enable   = debugger22.dbg_toggle.GetBitmap()
        bmp_stop     = common22.eng_stop.GetBitmap()
        bmp_pause    = debugger22.dbg_pause.GetBitmap() 
        bmp_end      = debugger22.dbg_end.GetBitmap()
        bmp_step     = debugger22.dbg_step.GetBitmap()
        bmp_stepin   = debugger22.dbg_step_in.GetBitmap()
        bmp_stepout  = debugger22.dbg_step_out.GetBitmap()
        bmp_bplist   = debugger22.dbg_bp_list.GetBitmap()

        #-----------------------------------------------------------------------
        #enable disable debugger toggle button
        self.AddTool( ID_DEBUG, bmp_enable, wx.ITEM_CHECK,
                    "Enable engine debugger",
                    "Enable the engine debugger mode")
        self.Bind(wx.EVT_TOOL, self.OnDebug, id=ID_DEBUG)

        self.AddSeparator()

        #pause/resume
        self._paused = False
        self.AddTool( ID_PAUSE, bmp_pause, wx.ITEM_CHECK,
                    'Pause running command', 
                    'Pause running command')
        self.Bind(wx.EVT_TOOL, self.OnPause, id=ID_PAUSE)

        #end debugging
        self.AddTool( ID_END, bmp_end, wx.ITEM_NORMAL,
                        'End debugging',
                        'End debugging and finish running command')
        self.Bind(wx.EVT_TOOL, self.OnEnd, id=ID_END)

        #stop running code button
        self.AddTool( ID_STOP, bmp_stop, wx.ITEM_NORMAL,
                    'Stop running code',
                    'Force running code to stop')
        self.Bind(wx.EVT_TOOL, self.OnStop, id=ID_STOP)

        self.AddSeparator()

        #step
        self.AddTool( ID_STEP, bmp_step, wx.ITEM_NORMAL,
                    'Step to next line',
                    'Step to next line of running command')
        self.Bind(wx.EVT_TOOL, self.OnStep, id=ID_STEP)

        #step in
        self.AddTool( ID_STEPIN, bmp_stepin, wx.ITEM_NORMAL,
                    'Step into the new scope', 
                    'Step into the new scope')
        self.Bind(wx.EVT_TOOL, self.OnStepIn, id=ID_STEPIN)

        #step out
        self.AddTool( ID_STEPOUT, bmp_stepout, wx.ITEM_NORMAL,
                    'Step out of the current scope', 
                    'Step out of the current scope')
        self.Bind(wx.EVT_TOOL, self.OnStepOut, id=ID_STEPOUT)

        self.AddSeparator()

        #breakpoints pane
        self.AddTool( ID_BPLIST, bmp_bplist, wx.ITEM_CHECK,
                    'Show/Hide breakpoint pane',
                    'Show/Hide breakpoint pane')
        self.Bind(wx.EVT_TOOL, self.OnBPPane, id=ID_BPLIST)

        #bind to the break_point pane events to update the toggle button
        # when shown/hidden
        bp_pane = self.Parent.bp_pane
        bp_pane.window.Bind( wx.EVT_SHOW, self.OnBPShow)

        self.Realize()

        #subscribe to engine/console tool messages
        self.tool.msg_node.subscribe( console_messages.CONSOLE_SWITCHED, 
                                        self.msg_console)
        self.tool.msg_node.subscribe(mb_protocol.SYS_NODE_CONNECT+'.Engine',
                                        self.msg_console) 
        self.tool.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine',
                                        self.msg_console) 

        self.tool.msg_node.subscribe( eng_messages.ENGINE_STATE_BUSY, 
                                        self.msg_engine)
        self.tool.msg_node.subscribe( eng_messages.ENGINE_STATE_DONE,
                                        self.msg_engine)
        self.tool.msg_node.subscribe( eng_messages.ENGINE_DEBUG, 
                                        self.msg_engine)

    #---messages----------------------------------------------------------------
    def msg_engine(self, msg):
        """
        Message handler for engine messages:
            ENGINE_BUSY
            ENGINE_DONE
            ENGINE_DEBUG* published messages
        """
        engname = msg.get_from()
        if self.console.is_engine_current(engname) is False:
            return
        self._update_tools()

    def msg_console(self,msg):
        """
        Message handler for console tool messages: 
            CONSOLE_SWITCHED
        """
        self._update_tools()

    def _update_tools(self):
        """
        Update the tools state.
        """
        #get the engine console
        eng = self.console.get_current_engine()

        #no engine/not an engine
        if eng is None:

            self.EnableTool(ID_DEBUG, False)
            self.ToggleTool(ID_DEBUG, False)
            self.EnableTool(ID_PAUSE, False)
            self.ToggleTool(ID_PAUSE, False)
            self.EnableTool(ID_END, False)
            self.EnableTool(ID_STEP  , False)            
            self.EnableTool(ID_STEPIN  , False)
            self.EnableTool(ID_STEPOUT  , False)
            return

        #is an engine update the tool state
        busy, debug, profile = eng.get_state()
        paused, can_stepin, can_stepout = eng.debugger.get_state()

        #debug button
        self.EnableTool(ID_DEBUG, True)
        self.ToggleTool(ID_DEBUG , debug)

        #paused button
        self.EnableTool(ID_PAUSE, debug)
        self.ToggleTool(ID_PAUSE, paused)
        self.EnableTool(ID_END, (busy and debug))

        if paused is True:
            self.SetToolShortHelp(ID_PAUSE,'Resume running command')
            self.SetToolLongHelp(ID_PAUSE,'Resume running command')
        else:
            self.SetToolShortHelp(ID_PAUSE,'Pause running command')
            self.SetToolLongHelp(ID_PAUSE,'Pause running command')

        #steps
        self.EnableTool(ID_STEP  , (paused and busy))            
        self.EnableTool(ID_STEPIN  , can_stepin)
        self.EnableTool(ID_STEPOUT  , can_stepout)

        self.Refresh()

    #---events------------------------------------------------------------------
    def OnDebug(self, event):
        """Enable engine debugger"""
        flag = event.IsChecked()
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.enable_debug(flag)

    def OnStop(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.stop()

    def OnPause(self,event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        #check if we are pausing or resumeing
        if eng.debugger.paused :
            res=eng.debugger.resume()
            res = not res
        else:
            res=eng.debugger.pause()

    def OnEnd(self,event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.end()

    def OnStep(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step()
    
    def OnStepIn(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step_in()

    def OnStepOut(self, event):
        eng = self.console.get_current_engine()
        if eng is None:
            return
        eng.debugger.step_out()

    def OnBPPane(self, event):
        #show/hide the breakpoint pane
        if self.Parent.bp_pane.IsShown():
            self.Parent.bp_pane.Hide()
            self.ToggleTool(ID_BPLIST, False)
            self.Refresh()
        else:
            self.Parent.bp_pane.Show()
            self.ToggleTool(ID_BPLIST, True)
            self.Refresh()
        self.Parent.auimgr.Update()

    def OnBPShow(self, event):
        #The breakpoint pane has been shown/hidden
        shown = event.GetShow()
        self.ToggleTool(ID_BPLIST, shown)
        self.Refresh()
        event.Skip()

#---Breakpoint edit dialog------------------------------------------------------
# used to edit breakpoints at a particular file/line in the editor.
#-------------------------------------------------------------------------------
class EditBreakpointDialog(wx.Dialog):
    def __init__(self, parent, filename, bpids, title='Edit Breakpoints'):
        """
        Open an edit breakpoint dialog for the breakpoints given in bpids.
        """
        wx.Dialog.__init__(self, parent, -1, title,
                            style=  wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                            size=(640,320)  )

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #the message panel is a sizer containing an icon and static text
        #shown when filename/lineno may be incorrect when the file
        #has unsaved modifications
        self.msgpanel = wx.Panel(self,-1)
        self.msgpanel.SetMinSize((-1,20))
        self.msgpanel.SetMaxSize((-1,20))
        self.msgpanel.SetBackgroundColour(wx.RED)
        msgsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.msgbmp = wx.StaticBitmap( self.msgpanel, -1,
                                        common16.dialog_warning.GetBitmap() )
        self.msgtext = wx.StaticText(self.msgpanel,-1,'This file has been modified - breakpoint line numbers will not be updated until the file is saved.')
        self.msgtext.Wrap(-1)
        msgsizer.Add(self.msgbmp,0,wx.ALL|wx.ALIGN_CENTER,10)
        msgsizer.Add(self.msgtext,1,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,10)
        self.msgpanel.SetSizer(msgsizer)
        sizer.Add(self.msgpanel,0,wx.EXPAND)

        app = wx.GetApp()
        editor = app.toolmgr.get_tool('Editor')
        page = editor.frame.notebook.GetPageFromPath( filename )
        if page is not None:
            if page.GetModify():
                self.msgpanel.Show()
            else:
                self.msgpanel.Hide()

        #notebook to hold info about the breakpoint(s) at this lineno
        #self.notebook = wx.Notebook(self,-1)
        self.notebook = aui.AuiNotebook(self, -1, 
                style = aui.AUI_NB_TOP| aui.AUI_NB_SCROLL_BUTTONS |
                        aui.AUI_NB_CLOSE_ON_ACTIVE_TAB)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnClosePage)
        self.bppanels = []

        for bpid in bpids:
            bppanel = BreakPointEditPanel( self.notebook, -1, bpid )
            self.notebook.AddPage( bppanel, 'Breakpoint: '+str(bpid) ) 
            self.bppanels.append( bppanel )
        sizer.Add( self.notebook, 1, wx.EXPAND|wx.ALL, 5)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)
        apply_but  = wx.Button(self, wx.ID_OK, "Apply")
        cancel_but = wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( apply_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( cancel_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        sizer.Add(butsizer,0, wx.ALL|wx.ALIGN_RIGHT)

        self.Bind(wx.EVT_BUTTON, self.OnApply, apply_but)

    def OnApply(self, event):
        #Apply button clicked pass to each bp panel
        for bppanel in self.bppanels:
            bppanel.Apply()
        event.Skip()

    def OnClosePage(self, event):
        num  = self.notebook.GetSelection()  
        page = self.notebook.GetPage(num)

        dlg = wx.MessageDialog(self, 
                "Clear breakpoint?", 
                "Clear breakpoint",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        result=dlg.ShowModal()
        dlg.Destroy()

        if result==wx.ID_YES:
            #clear the breakpoint
            app = wx.GetApp()
            editor = app.toolmgr.get_tool('Editor')
            bpid = page.bp['id']
            editor.clear_breakpoint(bpid)
            #remove the page from the internal list
            self.bppanels.remove(page)
            #allow the page to close
            event.Skip()
        else:
            event.Veto()

#---Breakpoint edit panel-------------------------------------------------------
# used in in EditBreakpoint dialog
class BreakPointEditPanel(wx.Panel):
    """Panel to hold/edit breakpoint data"""
    def __init__(self, parent, id, bpid):
        wx.Panel.__init__(self, parent, id)
        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #filename
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self, -1, 'Filename:', size=(100,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,5)
        self.fname = wx.TextCtrl(self,-1, '', size=(200,-1),style=wx.TE_READONLY|wx.TE_RIGHT)
        self.fname.SetBackgroundColour(label.GetBackgroundColour())
        hsizer.Add(self.fname,1,wx.ALIGN_CENTER_VERTICAL|wx.EXPAND|wx.RIGHT,5)

        label = wx.StaticText( self, -1, 'Line number:', size=(100,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,5)
        self.lineno = wx.TextCtrl(self,-1, '', size=(75,-1),style=wx.TE_READONLY)
        self.lineno.SetBackgroundColour(label.GetBackgroundColour())
        hsizer.Add(self.lineno,0,wx.ALIGN_CENTER_VERTICAL,0)
        sizer.Add(hsizer,0,wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,5)

        #condition tick box and text control
        self.cond_check = wx.CheckBox(self,-1,'Evaluate condition')
        self.cond_check.SetValue(False)
        self.Bind(wx.EVT_CHECKBOX, self.OnCondCheck, self.cond_check)
        sizer.Add(self.cond_check,0,wx.LEFT|wx.RIGHT|wx.TOP,5)
        self.cond = wx.TextCtrl(self,-1, '', size=(300,-1),style=wx.TE_MULTILINE)
        self.cond.Disable()
        sizer.Add(self.cond,1,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP,5)

        #ignore count tick box and value control
        self.ignore_check = wx.CheckBox(self,-1,'Ignore count (breakpoint will only trigger after being encountered this many times)')
        self.ignore_check.SetValue(False)
        self.Bind(wx.EVT_CHECKBOX, self.OnIgnoreCheck, self.ignore_check)
        sizer.Add(self.ignore_check,0,wx.LEFT|wx.RIGHT|wx.TOP,5)
        self.ignore = wx.TextCtrl(self,-1, '0')
        self.ignore.Disable()
        sizer.Add(self.ignore,0,wx.LEFT|wx.RIGHT|wx.TOP,5)

        #trigger count tick box and value control
        self.trigger_check = wx.CheckBox(self,-1,'Trigger count (breakpoint will only trigger this many times)')
        self.trigger_check.SetValue(False)
        self.Bind(wx.EVT_CHECKBOX, self.OnTriggerCheck, self.trigger_check)
        sizer.Add(self.trigger_check,0,wx.LEFT|wx.RIGHT|wx.TOP,5)
        self.trigger = wx.TextCtrl(self,-1, '1')
        self.trigger.Disable()
        sizer.Add(self.trigger,0,wx.ALL,5)

        self.SetBreakpoint(bpid)

    def SetBreakpoint(self, bpid):
        """
        Set the breakpoint which the panel is displaying
        """
        app = wx.GetApp()
        editor = app.toolmgr.get_tool('Editor')
        #get the breakpoint data
        bp = editor.get_breakpoint(bpid)
        if bp is None:
            return

        self.fname.SetValue( bp['filename'])
        self.lineno.SetValue( str(bp['lineno']))

        cond = bp['condition']
        if cond is None:
            self.cond_check.SetValue(False)
            self.cond.SetValue('')
            self.cond.Disable()
        else:
            self.cond_check.SetValue(True)
            self.cond.SetValue(cond)
            self.cond.Enable()

        ignore_count = bp['ignore_count']
        if ignore_count is None:
            self.ignore_check.SetValue(False)
            self.ignore.SetValue('')
            self.ignore.Disable()
        else:
            self.ignore_check.SetValue(True)
            self.ignore.SetValue(str(ignore_count))
            self.ignore.Enable()

        trigger_count = bp['trigger_count']
        if trigger_count is None:
            self.trigger_check.SetValue(False)
            self.trigger.SetValue('')
            self.trigger.Disable()
        else:
            self.trigger_check.SetValue(True)
            self.trigger.SetValue(str(trigger_count))
            self.trigger.Enable()

        self.bp = bp

    def Apply(self):
        """
        Apply any changes made to the breakpoint (modifies the breakpoint via
        the Editor tool)
        """
        changes = {}

        #check condition
        if self.cond_check.GetValue() is True:
            cond = self.cond.GetValue()
        else:
            cond = None
        if cond!=self.bp['condition']:
            changes['condition']=cond

        #check ignore count
        if self.ignore_check.GetValue() is True:
            try:
                ignore_count = int(self.ignore.GetValue())
            except:
                ignore_count = self.bp['ignore_count']
        else:
            ignore_count = None
        if ignore_count!=self.bp['ignore_count']:
            changes['ignore_count'] = ignore_count

        #check trigger count
        if self.trigger_check.GetValue() is True:
            try:
                trigger_count = int(self.trigger.GetValue())
            except:
                trigger_count = self.bp['trigger_count']
        else:
            trigger_count = None
        if trigger_count!=self.bp['trigger_count']:
            changes['trigger_count'] = trigger_count

        if changes!={}:
            app = wx.GetApp()
            editor = app.toolmgr.get_tool('Editor')
            editor.modify_breakpoint(self.bp['id'], **changes)

    def OnCondCheck(self,event):
        self.cond.Enable(event.IsChecked())

    def OnIgnoreCheck(self,event):
        self.ignore.Enable(event.IsChecked())

    def OnTriggerCheck(self,event):
        self.trigger.Enable(event.IsChecked())

#---Breakpoint list panel-------------------------------------------------------
# used in console/editor panes
#-------------------------------------------------------------------------------
class BreakPointListPanel(wx.Panel):
    def __init__(self, parent, tool):
        wx.Panel.__init__(self, parent, -1, size=(300,300))
        
        #store reference to editor tool
        self.editor = tool

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #-----------------------------------------------------------------------
        # Toolbar at top (add,remove,edit, clear all)
        self.tools = wx.ToolBar(self,-1,wx.DefaultPosition, 
                    wx.DefaultSize, style=wx.TB_HORIZONTAL | wx.TB_FLAT)

        #set the icon size
        size=wx.Size(16, 16)
        self.tools.SetToolBitmapSize(size)

        #load some icons
        add_bmp     = common16.add.GetBitmap()
        remove_bmp  = common16.remove.GetBitmap()
        clear_bmp   = common16.edit_delete.GetBitmap()
        edit_bmp    = editor_icons.edit_bp.GetBitmap()

        #add
        add_id = wx.NewId()
        tool = self.tools.AddLabelTool( add_id, "Add", add_bmp,
                            shortHelp='Add a new breakpoint',
                            longHelp='Add a new breakpoint')
        self.Bind(wx.EVT_TOOL, self.OnAdd, id=add_id)
        
        #remove
        remove_id = wx.NewId()
        self.tools.AddLabelTool( remove_id, "Remove", remove_bmp,
                            shortHelp='Remove selected breakpoint(s)',
                            longHelp='Remove selected breakpoint(s)')
        self.Bind(wx.EVT_TOOL, self.OnRemove, id=remove_id)

        #clear
        clear_id = wx.NewId()
        self.tools.AddLabelTool( clear_id, "Clear all", clear_bmp,
                            shortHelp='Clear all breakpoints',
                            longHelp='Clear all breakpoints')
        self.Bind(wx.EVT_TOOL, self.OnClearAll, id=clear_id)

        #edit
        edit_id = wx.NewId()
        self.tools.AddLabelTool( edit_id, "Edit", edit_bmp,
                            shortHelp='Edit selected breakpoints',
                            longHelp='Edit selected breakpoints')
        self.Bind(wx.EVT_TOOL, self.OnEdit, id=edit_id)

        self.tools.Realize()
        line = wx.StaticLine(self)

        sizer.Add(self.tools, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,2 )
        sizer.Add(line, 0, wx.EXPAND |wx.TOP |wx.BOTTOM,3) 
        #-----------------------------------------------------------------------

        #images to use for tree items
        self.ilist = wx.ImageList(16,16)
        self.filebmp = self.ilist.Add(common16.pythonfile16.GetBitmap())
        self.bpbmp = self.ilist.Add(editor_icons.bp_icon.GetBitmap())

        #breakpoint tree
        self.tree = wx.TreeCtrl(self, -1, style=wx.TR_DEFAULT_STYLE |
                               wx.TR_SINGLE| wx.TR_HIDE_ROOT)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeActivated, self.tree)
        self.tree.SetImageList(self.ilist)
        self.Update() #populate the tree control
        sizer.Add(self.tree,1,wx.EXPAND|wx.ALL,5)

        #subscribe to debugger breakpoint 
        self.editor.msg_node.subscribe( editor_messages.EDITOR_BREAKPOINT_SET, 
                                        self.msg_bp_set)
        self.editor.msg_node.subscribe( editor_messages.EDITOR_BREAKPOINT_CLEARED, 
                                        self.msg_bp_clear)
        self.editor.msg_node.subscribe( editor_messages.EDITOR_BREAKPOINT_CHANGED, 
                                        self.msg_bp_change)

    def Update(self):
        """
        Update the breakpoint tree
        """
        #clear and recreate
        self.tree.DeleteAllItems()
        root = self.tree.AddRoot('root')

        #get all files with breakpoints set from the Console
        files = self.editor.get_breakpoint_files()

        #add these files and the breakpoints to the tree control
        for file in files:
            #shorten the file name if neccessary
            value = file
            if len(value)>32:
                value = '...'+value[-32:]

            #add the file item
            file_item = self.tree.AppendItem(root, value)
            self.tree.SetItemImage(file_item, self.filebmp, wx.TreeItemIcon_Normal)
            self.tree.SetPyData( file_item, file )

            #add all the breakpoints in this file
            bps = self.editor.get_breakpoints(filename=file)

            #sort these into lineno groups
            lines = {}
            for bp in bps:
                line = bp['lineno']
                line_bps = lines.get( line, [])
                line_bps.append( bp )
                lines[line] = line_bps

            #add line no's and breakpoints.
            for line in lines:
                value = 'Line: '+str(line)
                line_bps = lines[line]
                line_item = self.tree.AppendItem(file_item, value )
                self.tree.SetPyData( line_item, (line, line_bps) )

                #add breakpoints
                for bp in line_bps:
                    value = 'Breakpoint id: '+str( bp['id'] )
                    bp_item = self.tree.AppendItem(line_item, value )
                    self.tree.SetItemImage(bp_item, self.bpbmp, wx.TreeItemIcon_Normal)
                    self.tree.SetPyData( bp_item, bp )
            
            #expand the tree
            self.tree.ExpandAll()

    def OnTreeActivated(self, event):
        item =  event.GetItem()
        parent = self.tree.GetItemParent( item )
        a_file = (parent.m_pItem == self.tree.RootItem.m_pItem)
        a_line = (not a_file) and self.tree.ItemHasChildren(item) 
        a_bp = (not a_line) or (not a_file)

        if a_file:
            # item is a file open in editor
            filename = self.tree.GetPyData( item )
            line = None
        elif a_line:
            # item is line open file and scroll to it
            #open the file 
            file_item = self.tree.GetItemParent(item)
            filename = self.tree.GetPyData( file_item )
            line, bps =  self.tree.GetPyData( item )
        else:
            #a breakpoint
            line_item = self.tree.GetItemParent(item)
            file_item = self.tree.GetItemParent(line_item)
            filename = self.tree.GetPyData( file_item )
            bp = self.tree.GetPyData(item)
            line = bp['lineno']
            
        #open the file and scroll to the line if necessary
        self.editor.frame.OpenFile(filename)
        if line is not None:
            page = self.editor.notebook.GetPageFromPath(filename)
            if page is not None:
                page.ScrollToLine(line-1)

    def OnAdd(self, event):
        d = SetBPDialog(self)
        res = d.ShowModal()
        d.Destroy()

    def OnEdit(self, event):
        item =  self.tree.GetSelection()
        if item.IsOk() is False:
            return
        parent = self.tree.GetItemParent( item )

        #get the selected breakpoint/lineno
        a_file = (parent.m_pItem == self.tree.RootItem.m_pItem)
        a_line = (not a_file) and self.tree.ItemHasChildren(item) 
        a_bp = (not a_line) or (not a_file)

        if a_file:
            # edit all breakpoints in file
            filename = self.tree.GetPyData( item )
            bps = self.editor.get_breakpoints(filename)

        elif a_line:
            # item is line open file and scroll to it
            #open the file 
            file_item = self.tree.GetItemParent(item)
            filename = self.tree.GetPyData( file_item )
            line, bps =  self.tree.GetPyData( item )
        else:
            #a breakpoint
            line_item = self.tree.GetItemParent(item)
            file_item = self.tree.GetItemParent(line_item)
            filename = self.tree.GetPyData( file_item )
            bps = [ self.tree.GetPyData(item) ]
        
        #dialog needs ids
        bpids = []
        for bp in bps:
            bpids.append(bp['id'])

        #open the edit breakpoint dialog
        dlg = EditBreakpointDialog( self, filename, bpids )
        res = dlg.ShowModal()
        dlg.Destroy()

    def OnRemove(self, event):
        item =  self.tree.GetSelection()
        if item.IsOk() is False:
            return
        parent = self.tree.GetItemParent( item )
        a_file = (parent.m_pItem == self.tree.RootItem.m_pItem)
        a_line = (not a_file) and self.tree.ItemHasChildren(item) 
        a_bp = (not a_line) or (not a_file)

        if a_file:
            # item is a file open in editor
            filename = self.tree.GetPyData( item )
            line = None
            msg =  "Remove all breakpoints in this file?"
            title= "Remove Breakpoints"
            
        elif a_line:
            # item is line open file and scroll to it
            #open the file 
            file_item = self.tree.GetItemParent(item)
            filename = self.tree.GetPyData( file_item )
            line, bps =  self.tree.GetPyData( item )
            msg =  "Remove all breakpoints at this line number?"
            title= "Remove Breakpoints"

        else:
            #a breakpoint
            line_item = self.tree.GetItemParent(item)
            file_item = self.tree.GetItemParent(item)
            filename = None
            bp = self.tree.GetPyData(item)
            line = bp['lineno']
            msg =  "Remove Breakpoint?"
            title= "Remove Breakpoint"

        #confirm dialog
        dlg = wx.MessageDialog(self, msg, title,
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        result=dlg.ShowModal()
        dlg.Destroy()
    
        if result==wx.ID_YES:
            if filename is None:
                #clear only a single breakpoint
                self.editor.clear_breakpoint( bp['id'] )
            else:
                #clear all in file (or in file at line number)
                self.editor.clear_breakpoints( filename, line)

    def OnClearAll(self, event):
        #confirm dialog
        dlg = wx.MessageDialog(self, 
                "Clear all breakpoints?", 
                "Clear all Breakpoints",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        result=dlg.ShowModal()
        dlg.Destroy()

        if result==wx.ID_YES:
            self.editor.clear_all_breakpoints()
            self.Update()

    #---messages----------------------------------------------------------------
    def msg_bp_set(self, msg):
        self.Update()

    def msg_bp_clear(self, msg):
        self.Update()

    def msg_bp_change(self, msg):
        self.Update()



#-------------------------------------------------------------------------------
# Graphical message dialog to explain set/edit/clearing
#-------------------------------------------------------------------------------
setbp = PyEmbeddedImage(
    "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")

class SetBPDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Set Breakpoints",
                            style= wx.DEFAULT_DIALOG_STYLE, size=(350,250))

        self.SetIcon( common16.help_browser.GetIcon() )
        dsizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self, -1)
        dsizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dsizer)

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)

        #nice picture
        bmp = wx.StaticBitmap(panel, -1, setbp.GetBitmap())
        sizer.Add(bmp,1, wx.ALIGN_CENTER|wx.ALL, 10)
    
        #Help text
        help = "Click next to the line number in an open file to set a breakpoint."
        text = controls.WWStaticText(panel, -1, help)
        font = text.GetFont()
        font.SetWeight(wx.BOLD)
        text.SetFont(font)
        sizer.Add(text, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        help = "Ctrl + Click to edit the breakpoint conditions."
        text = controls.WWStaticText(panel, -1, help)
        text.SetFont(font)
        sizer.Add(text, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        
        help = "Click an existing breakpoint to clear."
        text = controls.WWStaticText(panel, -1, help)
        text.SetFont(font)
        sizer.Add(text, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)

        #create static line and OK/Cancel button
        line = wx.StaticLine(panel,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)
        open_but  = wx.Button(panel, wx.ID_OPEN, "Open file")
        cancel_but = wx.Button(panel, wx.ID_CANCEL, "Done")
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( open_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( cancel_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        sizer.Add(butsizer,0, wx.ALL|wx.ALIGN_RIGHT)

        self.Bind(wx.EVT_BUTTON, self.OnOpenFile, open_but)
        panel.SetSizer(sizer)

    def OnOpenFile(self, event):
        #close this dialog
        self.Close()

        #Use the editor notebook open file interface
        app = wx.GetApp()
        editor = app.toolmgr.get_tool('Editor')
        editor.notebook.Open()
