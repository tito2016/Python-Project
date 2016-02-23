import wx
from ptk_lib import controls

#-------------------------------------------------------------------------------
class AppSettingsPanel(wx.Panel):
    def __init__    (self,parent):
        wx.Panel.__init__(self,parent,-1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        ##Message bus options
        msgbox = wx.StaticBox(self, -1, "MessageBus Port:")
        boldfont = msgbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        msgbox.SetFont(boldfont)

        msgsizer1 = wx.StaticBoxSizer(msgbox, wx.HORIZONTAL)
        sizer.Add(msgsizer1,1,wx.EXPAND|wx.ALL,5)
        s='Tools and engines that run as external processes communicate with the application by connecting to this port. This is also used to prevent a second instance of the application from starting.'
        t1 = controls.WWStaticText(self, -1, s)
        msgsizer1.Add(t1,1,wx.EXPAND|wx.ALL,5)
        self.msgport = wx.TextCtrl(self,-1,'6667',validator = controls.IntValidator())
        msgsizer1.Add(self.msgport,0,wx.ALL|wx.ALIGN_LEFT,5)

    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("App//")

        #load the messenger port
        port = cfg.ReadInt("message_bus_port",6666)
        self.msgport.SetValue(str(port))
        

    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("App//")

        #save the messenger port
        try:
            port = int(self.msgport.GetValue())
        except:
            port = 6667
        cfg.WriteInt("message_bus_port",port)

    
