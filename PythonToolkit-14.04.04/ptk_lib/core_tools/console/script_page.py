"""
The ConsolePage for scripts (not run as interactive engines)
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import time
import os
import signal
import sys

import wx
import wx.richtext as rt

from ptk_lib.controls import dialogs

from console_frame import ConsolePage
from console_dialogs import RunExternalDialog
import console_icons

#cursor navigation keys
NAVKEYS = ( wx.WXK_END  , wx.WXK_HOME,
            wx.WXK_LEFT , wx.WXK_NUMPAD_LEFT,
            wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT,
            wx.WXK_UP   , wx.WXK_NUMPAD_UP,
            wx.WXK_DOWN , wx.WXK_NUMPAD_DOWN,
            wx.WXK_PAGEDOWN, wx.WXK_PAGEUP )

class ScriptRTC(rt.RichTextCtrl):
    """
    RichTextCtrl console used in ScriptPage.
    """
    def __init__(self, parent, id):
        rt.RichTextCtrl.__init__(self, parent, id)

        #internals
        self.prompting = False     #prompting flag (user input allowed)
        self.promptpos = 0         #position in document where user input begins
        self.promptlen = 0         #length of the current prompt

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_TEXT_URL, self.OnLink)

        #create a context menu
        self.context_menu = wx.Menu()
        self.context_menu.Append(wx.ID_CUT, "Cut")
        self.context_menu.Append(wx.ID_COPY, "Copy")
        self.context_menu.Append(wx.ID_PASTE, "Paste")
        self.context_menu.Append(wx.ID_CLEAR, "Clear")
        self.context_menu.AppendSeparator()
        self.context_menu.Append(wx.ID_SELECTALL, "Select All")

        #context menu events
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnCMenuUpdateUI)
        self.Bind(wx.EVT_MENU, self.OnCut, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnClear, id=wx.ID_CLEAR)

    #---------------------------------------------------------------------------
    def PushInput(self, line):
        """
        Process a line of user input
        """
        self.Parent.process.GetOutputStream().write(line + '\n')
        self.WritePrompt('', False)

    def WritePrompt(self, prompt='>>> ', more=False):
        """
        Add a prompt to the console. 
        If more is True the prompt position will not be updated but the prompt 
        (a continuation prompt) will be added. 
        """
        #write the prompt
        self.prompting = True
        self.SetInsertionPoint(self.GetLastPosition())
        self.WriteText(prompt)

        #If this is not a continuation then we want to update the prompt 
        #position to prevent previous commands/output from being edited
        if more is False:
            #update prompt position and prompt length
            self.promptpos = self.GetLastPosition()
            self.promptlen = len(prompt)

    def ClearPrompt(self):
        """
        Clear the current prompt
        """
        self.prompting = False
        #clear the prompt and any new input.
        self.Delete( (self.promptpos-self.promptlen, self.GetLastPosition() ) ) 

    def WriteStdOut(self, text):
        """Write StdOut text"""
        #store old insertation point and selection
        old = self.GetInsertionPoint()
        sel = self.GetSelection()

        #set insertation point before current user input
        self.SetInsertionPoint(self.promptpos-self.promptlen)

        #add the text
        self.WriteText(text)

        #restore user input point relative to new text
        n = len(text)
        if old >= self.promptpos:
            self.SetInsertionPoint(old+n)
        else:
            self.SetInsertionPoint(old)

        #restore selection relative to the new text
        if sel[0] != sel[1]:
            if sel[0] >= self.promptpos:
                new_start = sel[0]+n
            else:
                new_start = sel[0]

            if sel[1] > self.promptpos:
                new_end = sel[1]+n
            else:
                new_end = sel[1]
            #text was selected, restore this state
            self.SetSelection( new_start, new_end )

        #update the promptpos
        self.promptpos = self.promptpos + n

        #scroll to keep visible
        self.ShowPosition(old+n)

    def WriteStdErr(self, text):
        """Write StdErr text"""
        #store old insertation point and selection
        old = self.GetInsertionPoint()
        sel = self.GetSelection()

        #set insertation point before current user input
        self.SetInsertionPoint(self.promptpos-self.promptlen)

        #set text styles
        self.BeginTextColour((255, 0, 0))

        #try to identify any file in the traceback
        i0 = text.find('File')
        remaining = text
        while i0 is not -1:
            i1 = remaining.find('\n', i0)

            #split the string into before, the file, and after
            start = remaining[:i0]
            file_line = remaining[i0:i1]
            remaining = remaining[i1:]

            self.WriteText(start)

            self.BeginUnderline()
            self.BeginURL(file_line)
            self.WriteText(file_line)
            self.EndURL()
            self.EndUnderline()

            #search for next file
            i0 = remaining.find('File')

        else:
            #add any remaining text
            self.WriteText(remaining)

        #end text styles
        self.EndTextColour()

        #restore user input point relative to new text
        n = len(text)
        if old >= self.promptpos:
            self.SetInsertionPoint(old+n)
        else:
            self.SetInsertionPoint(old)

        #restore selection relative to the new text
        if sel[0] != sel[1]:
            if sel[0] >= self.promptpos:
                new_start = sel[0]+n
            else:
                new_start = sel[0]

            if sel[1] > self.promptpos:
                new_end = sel[1]+n
            else:
                new_end = sel[1]
            #text was selected, restore this state
            self.SetSelection( new_start, new_end )

        #update the promptpos
        self.promptpos = self.promptpos + n

        #scroll to keep visible
        self.ShowPosition(old+n)

    def WriteMsg(self, text):
        """Write text from a control message"""
        #store old insertation point and selection
        old = self.GetInsertionPoint()
        sel = self.GetSelection()

        #set insertation point before current user input
        self.SetInsertionPoint(self.promptpos-self.promptlen)

        #set text styles
        self.BeginTextColour((0, 0, 255))

        #add the text
        self.WriteText(text)

        #end text styles
        self.EndTextColour()

        #restore user input point relative to new text
        n = len(text)
        if old >= self.promptpos:
            self.SetInsertionPoint(old+n)
        else:
            self.SetInsertionPoint(old)

        #restore selection relative to the new text
        if sel[0] != sel[1]:
            if sel[0] >= self.promptpos:
                new_start = sel[0]+n
            else:
                new_start = sel[0]

            if sel[1] > self.promptpos:
                new_end = sel[1]+n
            else:
                new_end = sel[1]
            #text was selected, restore this state
            self.rtc.SetSelection( new_start, new_end )

        #update the promptpos
        self.promptpos = self.promptpos + n

        #scroll to keep visible
        self.ShowPosition(old+n)

    #---cut/copy/paste----------------------------------------------------------
    def Cut(self):
        """
        Cut selection if user entry otherwise copy
        """
        #in an editable region
        currentpos  = self.GetInsertionPoint()
        if currentpos >= self.promptpos:
            rt.RichTextCtrl.Cut(self)
        else:
            rt.RichTextCtrl.Copy(self)

    def Copy(self):
        """
        Copy the selection.
        """
        #can always copy
        rt.RichTextCtrl.Copy(self)

    def Paste(self):
        """
        Paste from clipboard if at an editable point
        """
        #in an editable region
        currentpos  = self.GetInsertionPoint()
        if currentpos >= self.promptpos:
            rt.RichTextCtrl.Paste(self)

    def Clear(self):
        """Clears the console"""
        if self.prompting:
            self.Delete( (0, self.promptpos - self.promptlen ) )
        else:
            rt.RichTextCtrl.Clear(self)
        self.promptpos =  self.promptlen
        self.SetInsertionPoint( self.GetLastPosition())

    #---events------------------------------------------------------------------
    def OnKeyDown(self, event):
        """Key down event handler."""
        #get key info
        key         = event.GetKeyCode() #always capital letters here
        controlDown = event.CmdDown()    #use CmdDown to support mac command button and win/linux ctrl
        altDown     = event.AltDown()
        shiftDown   = event.ShiftDown()

        #positions in rtc
        currentpos  = self.GetInsertionPoint()
        endpos      = self.GetLastPosition()

        #selecting?
        from_pos,to_pos = self.GetSelection()
        if from_pos==to_pos:
            selecting = False
        else:
            selecting = True

        #in an editable region
        if currentpos >= self.promptpos:
            edit = True
        else:
            edit = False
        edit = edit and self.prompting

        #line of input entered.
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            if self.prompting:
                line = self.GetRange( self.promptpos, endpos )
                self.PushInput( line )
            
        #backspace
        elif key is wx.WXK_BACK:
            #prevent backspace at promptpos (deletes previous char)
            if (currentpos>(self.promptpos)):
                    event.Skip()

        #Cut / Copy /Paste
        elif (shiftDown and key == wx.WXK_DELETE):
            self.Cut()

        elif (controlDown and key==ord('X')):
            self.Cut()

        elif controlDown and not shiftDown and key==wx.WXK_INSERT:
            self.Copy() 

        elif (controlDown and key==ord('C')):
            if self.Parent.IsAlive():
                self.Parent.Interupt()
            else:
                self.Copy()

        elif (shiftDown and not controlDown and key == wx.WXK_INSERT):
            self.Paste()

        elif (controlDown and key==ord('V')):
            self.Paste()

        # Clear any user input on escape key
        elif(key==wx.WXK_ESCAPE):
            self.Delete( (self.promptpos, endpos) )

        #Allow navigation in uneditable regions
        elif key in NAVKEYS: 
            event.Skip()

        #catch the home key and shift down
        elif key == wx.WXK_HOME:
            if shiftDown is True:
                self.SetSelection(self.promptpos, currentpos)
            else:
                self.SetInsertionPoint(self.promptpos)

        elif edit is True:
            event.Skip()

    def OnLink(self, event):
        """Event handler for links in the RTC"""
        file_line = event.GetString()

        #split into file and lineno
        i0 = file_line.find('"')
        if i0 == -1:
            return

        i1 = file_line.find('"', i0+1)
        if i1 == -1:
            return

        file = file_line[i0+1:i1]

        #find lineno
        i0 = file_line.find('line')
        i1 = file_line.find(',', i0)
        if (i0==-1) or (i1==-1):
            lineno = 0
        else:
            lineno = int( file_line[i0+5: i1] ) 

        editor = wx.GetApp().toolmgr.get_tool('Editor')
        editor.edit_file(file, lineno)

    #Context menu events
    def OnContextMenu(self, evt):
        """Create and display a context menu for the shell"""
        self.PopupMenu(self.context_menu)
        
    def OnCMenuUpdateUI(self, evt):
        """disable the context menu actions that are not possible"""

        #in an editable region
        currentpos  = self.GetInsertionPoint()
        if currentpos >= self.promptpos:
            edit = True
        else:
            edit = False

        #selecting
        from_pos, to_pos = self.GetSelection()
        if from_pos == to_pos:
            selecting = False
        else:
            selecting = True

        id = evt.Id
        if id == wx.ID_CUT:
            evt.Enable(edit and selecting)
        elif id == wx.ID_COPY:
            evt.Enable(selecting)
        elif id == wx.ID_PASTE:
            evt.Enable(edit and self.CanPaste())

    # context menu events
    def OnCut(self,evt):
        """Cut event handler"""
        self.Cut()

    def OnCopy(self,evt):
        """Copy event handler"""
        self.Copy()

    def OnPaste(self,evt):
        """Paste event handler"""
        self.Paste()

    def OnClear(self,evt):
        """Clear event handler"""
        self.Clear()

    def OnSelectAll(self,evt):
        """Select all menu handler"""
        self.SelectAll()

   
#-------------------------------------------------------------------------------
class ScriptPage(wx.Panel, ConsolePage):
    """
    A page providing a control console for scripts (not run as interactive 
    engines). Using a RichTextCtrl subclass to display IO.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        #console page base class initialisation
        ConsolePage.__init__(self)
    
        #console control
        self.rtc = ScriptRTC(self, -1)

        #layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.rtc, 1, wx.EXPAND, 0 )
        self.SetSizer(sizer)

        #process attributes
        self.process = None
        self.pid = None
        self.runtime = None
        self.filepath = None
        self.args = None

        #bind events
        self.Bind(wx.EVT_END_PROCESS, self.OnProcessEnded)

    #---Script process methods--------------------------------------------------
    def StartProcess(self, filepath, args):
        """
        Start the process
        """
        #launch process
        self.filepath = filepath
        self.args = args
    
        if sys.platform=='win32':
            cmd = 'pythonw -u "'+self.filepath+'"'
        else:
            cmd = 'python -u "'+self.filepath+'"'
        
        for arg in args:
            cmd = cmd+' '+arg
        log.debug('cmd: '+cmd)

        self.process = wx.Process(self)
        self.process.Redirect();
        self.pid = wx.Execute(cmd, wx.EXEC_ASYNC|wx.EXEC_NOHIDE, self.process)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.runtime = time.time()

        text = 'Executing: '+cmd +'\n(Process pid: '+str(self.pid)+')\n'
        self.rtc.WriteMsg(text)
        self.rtc.WritePrompt('', False)

        n = self.Parent.GetPageIndex(self)
        name = os.path.basename( filepath )
        self.Parent.SetPageText(n, name )

    def KillProcess(self):
        """
        Kill the process that this page is controlling.
        """
        if self.process is not None:
            self.process.CloseOutput()
            #try to terminate, then kill
            if wx.Process.Kill(self.pid, wx.SIGTERM) != wx.KILL_OK:
                wx.Process.Kill(self.pid, wx.SIGKILL, flags=wx.KILL_CHILDREN)

    def Interupt(self):
        """
        Send a keyboard interupt to the process
        """
        os.kill(self.pid, signal.SIGINT)

    def IsAlive(self):
        """
        Is the process that this page is controlling still alive.
        """
        if self.process is None:
            return False
        else:
            return True

    def Restart(self):
        """
        Restart the process
        """
        if self.IsAlive():
            raise Exception('Already active')
        if self.filepath is None:
            raise Exception('No script filepath set yet!')
        self.StartProcess(self.filepath, self.args)

    #---events------------------------------------------------------------------
    def OnIdle(self, event):
        """
        Idle event handler - used to check for StdIO from the running process
        """
        if self.process is None:
            return

        # do process output stream (wx.Process input stream!)
        stream = self.process.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            self.rtc.WriteStdOut(text)

        # do process error stream 
        stream = self.process.GetErrorStream()
        if stream.CanRead():
            text = stream.read()
            self.rtc.WriteStdErr(text)

    def OnProcessEnded(self, evt):
        """
        Process ended handler
        """
        pid = evt.GetPid()
        exitcode = evt.GetExitCode()

        #clear any process output waiting to be read
        stream = self.process.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            self.rtc.WriteStdOut(text)

        #clear any process output waiting to be read
        stream = self.process.GetErrorStream()
        if stream.CanRead():
            text = stream.read()
            self.rtc.WriteStdErr(text)

        #clear any unsent user entry
        self.rtc.ClearPrompt() 

        #write message
        text = '\nProcess (pid: '+str(pid)+') ended.\n'
        self.rtc.WriteMsg(text)
        text ='Exit code: '+str(exitcode)+'\n'
        self.rtc.WriteMsg(text)
        text = 'Runtime: ' +str(time.time() - self.runtime)+'\n'
        self.rtc.WriteMsg(text)

        #destroy process
        self.process.Destroy()
        self.process = None
        self.pid = None

        self.Unbind( wx.EVT_IDLE, handler=self.OnIdle)

    #---ConsolePage methods-----------------------------------------------------
    def LoadOptions(self):
        """
        Load and apply any options relevant to the console
        """
        pass

    def OnPageStop(self):
        """
        Called to stop/keyboard interupt this console page
        """
        self.Interupt()

    def OnPageClear(self):
        """
        Called to clear this console page
        """
        self.rtc.Clear()

    def OnPageSelect(self, event):
        """
        Called when this console page is selected
        """
        #make sure contents is upto date.
        self.OnIdle(event)

    def OnPageClose(self, event):
        """
        Called when the console page is about to be closed. 
        """
        #check still alive, if not go ahead and close
        if self.IsAlive() is False:
            return event.Skip()

        #otherwise let user decide
        res = dialogs.ConfirmDialog('Kill running script?',
                                    'Kill Script?')
        if res is False:
            return event.Veto()
            
        self.KillProcess()
        return event.Skip()

    def GetPageMenu(self):
        """
        Returns a new Settings menu object for this console.
        This should be destroyed when finished with.
        """
        menu = wx.Menu()

        #Restart
        restart_item = wx.MenuItem( menu, -1 ,"Restart", 
                           'Restart the finsished script)',
                            wx.ITEM_NORMAL)
        restart_item.SetBitmap(console_icons.run.GetBitmap())
        menu.AppendItem(restart_item)
        menu.Bind(wx.EVT_MENU, self.OnRestart, restart_item)

        #edit script arguments
        edit_item = wx.MenuItem( menu, -1 ,"Edit arguments", 
                           'Edit the script arguments',
                            wx.ITEM_NORMAL)
        edit_item.SetBitmap(console_icons.console_settings.GetBitmap())
        menu.AppendItem(edit_item)
        menu.Bind(wx.EVT_MENU, self.OnEdit, edit_item)

        menu.AppendSeparator()

        #Stop/Keyboard interupt
        stop_item = wx.MenuItem( menu, -1 ,"Stop/Interupt    [Ctrl+C]", 
                           'Stop running script via a keyboard interrupt (Ctrl+c)',
                            wx.ITEM_NORMAL)
        stop_item.SetBitmap(console_icons.engine_stop.GetBitmap())
        menu.AppendItem(stop_item)
        menu.Bind(wx.EVT_MENU, self.OnStop, stop_item)

        #Kill
        kill_item = wx.MenuItem( menu, -1 ,'Kill process', 
                           'Kill the engine process', wx.ITEM_NORMAL)
        kill_item.SetBitmap(console_icons.kill.GetBitmap())
        menu.AppendItem(kill_item)
        menu.Bind(wx.EVT_MENU, self.OnKill, kill_item)

        if self.IsAlive():
            menu.Enable(restart_item.GetId(), False)
            menu.Enable(edit_item.GetId(), False)
            menu.Enable(stop_item.GetId(), True)
            menu.Enable(kill_item.GetId(), True)
        else:
            menu.Enable(restart_item.GetId(), True)
            menu.Enable(edit_item.GetId(), True)
            menu.Enable(stop_item.GetId(), False)
            menu.Enable(kill_item.GetId(), False)

        return menu

    #---page menu events--------------------------------------------------------
    def OnRestart(self, event):
        """
        Control menu handler
        """
        self.Restart()

    def OnEdit(self, event):
        """
        Control menu handler
        """
        d = RunExternalDialog(self.Parent, 'Edit script arguments')
        d.SetValue( self.filepath, self.args)
        res = d.ShowModal()
        if res==wx.ID_OK:
            filepath,args = d.GetValue()
            #store and restart
            self.filepath = filepath
            self.args = args
            self.restart()
        d.Destroy()
        

    def OnStop(self, event):
        """
        Control menu handler
        """
        self.Interupt()
        
    def OnKill(self, event):
        """
        Control menu handler
        """
        res = dialogs.ConfirmDialog('Kill running script?',
                                    'Kill Script?')
        if res is False:
            return False
            
        self.KillProcess()



