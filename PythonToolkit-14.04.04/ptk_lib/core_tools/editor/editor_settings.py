"""
EditorSettingsPanel - for editor options
"""
import wx

#-------------------------------------------------------------------------------
class EditorSettingsPanel(wx.Panel):
    def __init__    (self,parent):
        wx.Panel.__init__(self,parent,-1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        app = wx.GetApp()
        cfg = wx.Config(app.GetAppName())
        cfg.SetPath("Editor//")

    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        app = wx.GetApp()
        cfg = wx.Config(app.GetAppName())
        cfg.SetPath("Editor//")

        #flush at end to ensure settings are written
        cfg.Flush()