"""
CommandHistory Tool

Core tool providing the consoles command history and a pane interface in the 
main console window.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui
import os
import shelve
import time

from ptk_lib.engine import eng_messages

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.misc import USERDIR

from cmdhist_control import CmdHistControl
from cmdhist_settings import HistorySettingsPanel
import cmdhist_icons

#---Addressed message subjects--------------------------------------------------
#show the command history pane, data=(), result=None
SHOW = 'Show'

#---the tools class-------------------------------------------------------------
class CmdHistoryTool(Tool):
    name = 'CmdHistory'
    descrip = 'Core tool for controlling/accessing the command history'
    author = 'T.Charrett'
    requires = ['Console']           
    core = True            
    icon = cmdhist_icons.cmdhistory32
    
    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #the command history file
        self.filename = 'cmdhist.hist'

        #the command history and max length
        self.hist = []
        self.histmax=5000

        #attributes for searching in history
        self.offset = -1
        self.cursearch = ''
    
        #load settings
        self.LoadOptions()

        #load history
        self.LoadHistory()

        #add session started tag
        s = '#Session started : '+time.ctime()
        self.hist.insert(0,s)

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('CmdHistory')
        self.msg_node.connect(self.msg_bus)

        #register message handlers
        self.msg_node.set_handler(SHOW,self.msg_show)
        self.msg_node.subscribe('App.Exit', self.msg_app_exit)
        self.msg_node.subscribe(eng_messages.ENG_LINE_PROCESSED, self.msg_eng_line)

        ##---GUI Elements ------------------------------------------------------
        
        #create the console frame pane
        contool = self.app.toolmgr.get_tool('Console')
        self.cmdhist = CmdHistControl(contool.frame, self)
        pane = aui.AuiPaneInfo()

        #setup how to display this panel
        name='Command History'
        pane.Name(name) #id name
        pane.Caption(name) # caption
        pane.Right() #position
        pane.Layer(1)
        pane.Position(0)
        pane.Row(0)
        pane.CloseButton(True) #close button
        pane.MaximizeButton(True)
        pane.MinimizeButton(True)
        pane.Floatable(True)
        pane.BestSize( (350,400) )
        pane.MinSize( (350,300) )
        pane.DestroyOnClose(False)
        contool.frame.auimgr.AddPane(self.cmdhist, pane)

        #add a menu item to the tools menu to show and hide our pane
        bmp = cmdhist_icons.cmdhistory16.GetBitmap()
        contool.add_menu_item('tools', wx.NewId(), 'Command History',
                        'Open the command history pane', self.on_show, bmp)

        taskicon = self.toolmgr.get_tool('TaskIcon')
        taskicon.add_settings_item( 'Command history', HistorySettingsPanel,bmp)
                                    
        log.info('Done Initialising tool')
    #---interfaces--------------------------------------------------------------
    def Show(self):
        """
        Show the CommandHistory pane in the console window.
        """
        contool = self.app.toolmgr.get_tool('Console')
        pane = contool.frame.auimgr.GetPane('Command History')
        pane.Show()
        contool.frame.auimgr.Update()

    def LoadOptions(self):
        """
        Loads/Reloads the settings for the command history
        """
        cfg = self.app.GetConfig()
        cfg.SetPath("CmdHistory//")
        self.histmax = cfg.ReadInt("max_history_length",5000)
        self.filename = cfg.Read("history_file",USERDIR + 'cmdhist.hist')

    def SaveOptions(self):
        """
        Save the options
        """
        cfg = self.app.GetConfig()
        cfg.SetPath("CmdHistory//")
        cfg.WriteInt("max_history_length",self.histmax)
        cfg.Write("history_file",self.filename)

    def SetFile(self, filename): 
        """
        Set the path to store the current command history.
        """
        self.filename = filename
        self.SaveOptions()

    def SaveHistory(self, filename=None):
        """
        Save the history to file if None specified the current file is saved
        """
        log.info('Saving command history')
        if filename is None:
            filename=self.filename
        #open shelf file
        shelf = shelve.open(filename)
        shelf['history']=self.hist
        #close shelf
        shelf.close()

    def LoadHistory(self, filename=None):
        """
        Load the history from a file if None specified the current file is loaded
        """
        log.info('Loading command history')
        if filename is None:
            filename=self.filename
        try:
            shelf = shelve.open(filename)
        except:
            self.filename = USERDIR + 'cmdhist.shelf'
            shelf = shelve.open(self.filename)

        self.hist = shelf.get('history',[])
        shelf.close()

    def ImportHistory(self, filename):
        """
        Import the commands from a file into the history
        """
        #check file exists
        if os.path.exists(filename) is False:
            return
        root,ext = os.path.splitext(filename)
        if ext==".py":
            #load from source
            f = open(filename,'r')
            lines = f.readlines()
            f.close()
        else:
            #open as shelf
            try:
                shelf = shelve.open(filename)
                lines = shelf.get('history',[])
                lines.reverse()
                shelf.close() 
            except:
                lines = []

        #add commands after removing any extra \n
        for line in lines:
            if line[-1]=='\n':
                line = line[:-1]
            self.hist.insert(0, line )
        
        #check history length
        while len(self.hist)>self.histmax:
            self.hist.pop(-1)
        
        #publish change messaged
        self.tool.msg_node.publish_msg('Console.CmdHistory.Changed',())

    def SetSearchString(self, searchstr=''):
        """
        Sets the string to search for in the history (also resets position)
        """
        if type(searchstr) == unicode:
            try:
                searchstr = searchstr.encode(wx.GetDefaultPyEncoding())
            except UnicodeEncodeError:
                pass # otherwise leave it alone
        self.cursearch = searchstr
        self.offset=-1

    def GetPreviousCommand(self):
        """
        Get the previous(older)command from the history.
        If the search string has been set the history will be searched and the 
        previous match returned.
        """
        self.offset = self.offset+1
        cmd = self.GetCommand(self.offset,self.cursearch)
        if cmd is None:
            #no matches, reset offset and return the search string
            self.offset = -1
            return self.cursearch
        return cmd

    def GetNextCommand(self):
        """
        Get the next (more recent) command from the history. 
        If the search string has been set the history will be searched and the 
        next match returned.
        """
        self.offset = self.offset-1
        cmd = self.GetCommand(self.offset,self.cursearch)
        if cmd is None:
            #no matches, reset offset and return the search string
            self.offset = -1
            return self.cursearch
        return cmd

    def GetPosition(self):
        return self.offset

    def SetPosition(self,n=-1):
        """
        Set the position in the history
        """
        self.offest = n

    def AddCommand(self, cmdstring):
        """
        Add a command to the history.
        """
        #check that the command is not the same as the last command
        if len(self.hist)==0:
            lastcmd=None
        else:
            lastcmd=self.hist[0]
        
        #add to history if not the same as last command
        if (cmdstring!='') and (cmdstring!=lastcmd):
            self.hist.insert(0, cmdstring )
            #publish command added message
            self.msg_node.publish_msg('Console.CmdHistory.Add',(cmdstring,))

        #check history length
        while len(self.hist)>self.histmax:
            self.hist.pop(-1)

    def GetCommand(self, n, startstr=''):
        """
        Get the nth command from the history. If startstr is given then the 
        history will be searched for commands beginning startstr and the nth 
        match returned. If n is greater than matching commmands or the history 
        length then None will be returned.
        """
        #return none from negative n
        if n <0:
            return None

        #by pass the search if startstr is empty
        if startstr == '':
            #check n is not greater than history length
            if n>len(self.hist)-1:
                return None
            #return the command at position n
            return self.hist[n]

        #loop over history until the nth item
        c=-1
        for cmd in self.hist:
            #search for startstr and add to the results list
            if cmd.startswith(startstr):
                c+=1
            #check if n has been reached
            if c==n:
                return cmd
        #if n was never reached return None
        return None

    def ClearHistory(self):
        """Clears the command history"""
        self.hist=[]
        self.SaveHistory()
        #publish history cleared message
        self.msg_node.publish_msg('Console.CmdHistory.Changed',())
        
    #---message handlers--------------------------------------------------------
    def msg_show(self, msg):
        self.Show()

    def msg_app_exit(self,msg):
        """
        Listener for App.Exit message
        Save history and settings on application exit
        """
        self.SaveOptions()
        self.SaveHistory()

    def msg_eng_line(self, msg):
        """
        Listener for eng_messages.ENG_LINE_PROCESSED messages which are 
        published after the engine processes a line pushed from the console.
        """
        line,type = msg.get_data()
        line = line.strip('\n')
        self.AddCommand(line)

    #---event handlers----------------------------------------------------------
    def on_show(self,event):
        """
        wxEvent handler for menu items.
        """
        self.Show()
