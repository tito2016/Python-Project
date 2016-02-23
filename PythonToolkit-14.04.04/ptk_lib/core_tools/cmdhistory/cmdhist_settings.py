import wx
from ptk_lib.misc import USERDIR
from ptk_lib import controls

#-------------------------------------------------------------------------------
class HistorySettingsPanel(wx.Panel):
    def __init__    (self,parent):
        wx.Panel.__init__(self,parent,-1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
                
        ##Command history settings
        histbox = wx.StaticBox(self, -1, "Command History settings:")
        boldfont = histbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        histbox.SetFont(boldfont)
        histsizer1 = wx.StaticBoxSizer(histbox, wx.VERTICAL)
        histsizer2 = wx.FlexGridSizer(2,3,0,0)
        histsizer2.AddGrowableCol(1)
        histsizer1.Add(histsizer2,1,wx.EXPAND,0)
        sizer.Add(histsizer1,1,wx.EXPAND|wx.ALL,5)

        #maximium history length
        t = wx.StaticText(self,-1,'Maximium history length:')
        histsizer2.Add(t,1,wx.ALIGN_CENTER_VERTICAL|wx.ALL,10)
        self.histlen = wx.TextCtrl(self,-1,'5000',validator = controls.IntValidator())
        histsizer2.Add(self.histlen,0,wx.ALL|wx.ALIGN_LEFT,10)
        
        #clear history button
        b = wx.Button(self,-1,'Clear history')
        histsizer2.Add(b,0,wx.ALL|wx.ALIGN_LEFT,10)
        self.Bind(wx.EVT_BUTTON, self.OnClearHist,b)
        
        #history file
        t = wx.StaticText(self,-1,'Command history file:')
        histsizer2.Add(t,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,10)
        self.histfile = wx.TextCtrl(self,-1,'')
        histsizer2.Add(self.histfile,1,wx.EXPAND|wx.ALL,10)
        
        #set file button
        b = wx.Button(self,-1,'Set file')
        histsizer2.Add(b,0,wx.ALL|wx.ALIGN_LEFT,10)
        self.Bind(wx.EVT_BUTTON, self.OnSetFile,b)

    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        app = wx.GetApp()
        cfg = app.GetConfig()
        cfg.SetPath("CmdHistory//")

        #load the max length of history
        length = cfg.ReadInt("max_history_length",5000)
        self.histlen.SetValue(str(length))

        #load the command history file
        self.file = cfg.Read("history_file",USERDIR + 'cmdhist.hist')
        self.histfile.SetValue(self.file)

    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        app = wx.GetApp()
        cfg = app.GetConfig()
        cfg.SetPath("CmdHistory//")
        
        #save the max history length
        try:
            length = int(self.histlen.GetValue())
        except:
            length = 5000
        cfg.WriteInt("max_history_length",length)

        #save the command history
        cfg.Write("history_file",self.histfile.GetValue())
        cfg.Flush()

        #update the active command history settings
        app = wx.GetApp()
        cmdhist = app.toolmgr.get_tool('CmdHistory')
        cmdhist.LoadOptions()

    #---events------------------------------------------------------------------
    def OnClearHist(self,event):
        app = wx.GetApp()
        cmdhist = app.toolmgr.get_tool('CmdHistory')
        cmdhist.ClearHistory()   

    def OnSetFile(self,event):
        app = wx.GetApp()
        dlg = wx.FileDialog(
                self, message='Set active history file location',
                defaultDir=app.ptkdir,
                defaultFile="cmdhist.hist",
                wildcard = "History file (*.hist)|*.hist",
                style= wx.SAVE | wx.OVERWRITE_PROMPT
                )
        #only save if not cancelled.
        if dlg.ShowModal() != wx.ID_OK:
            return

        # get the enetered file path
        path = dlg.GetPath()
        app = wx.GetApp()
        cmdhist = app.toolmgr.get_tool('CmdHistory')
        cmdhist.SetFile(path)
        cmdhist.SaveHistory()
        self.histfile.SetValue(path)

