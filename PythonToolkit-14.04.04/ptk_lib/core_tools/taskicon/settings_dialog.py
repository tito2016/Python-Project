"""
The Settings/Preferences dialog and associated classes:

SettingsTreeBook - custom treebook control for settings dialog
SettingsDialog - the main program preferences dialog
"""
import wx
from ptk_lib.controls import AddressedTreeCtrl

class SettingsTreeBook(wx.Panel):
    def __init__(self,parent,id):
        wx.Panel.__init__(self,parent,id)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        #create the tree
        self.tree = AddressedTreeCtrl(self, id=-1, size=(200,-1), 
                                    style=wx.TR_HIDE_ROOT|wx.TR_LINES_AT_ROOT|
                                    wx.TR_HAS_BUTTONS|wx.BORDER_SUNKEN)
        self.root = self.tree.AddRoot('Settings',data=None)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)

        #create the sizer to hold/display the pages
        self.contents = wx.BoxSizer(wx.HORIZONTAL)

        #current page - set to a blank panel
        self.blank = wx.Panel(self,-1)
        self.contents.Add(self.blank,1,wx.EXPAND,0)
        self.current = self.blank

        sizer.Add(self.tree,0,wx.EXPAND|wx.ALL,2)
        sizer.Add(self.contents,1,wx.EXPAND|wx.ALL,2)
        self.SetSizer(sizer)

        self.pages = []

    def AddPage(self,address='\\child', panel=None, image=-1):
        #add to tree
        self.tree.AddItem(address,panel, image)
        #add the panel to the sizer
        if panel is not None:
            self.contents.Add(panel,1,wx.EXPAND,0)
            panel.Hide()
            self.pages.append(panel)
        self.Layout()

    def OnSelChanged(self,event):
        item = event.GetItem()
        panel = self.tree.GetItemPyData(item)
        #hide current
        self.current.Hide()
        if panel is None:
            self.current = self.blank
            #expand children
            self.tree.Expand(item)
        else:
            self.current = panel
        self.current.Show()
        self.Layout()
    
    def GetCurrentPage(self):
        if self.current!=self.blank:
            return self.current
        else:
            return None

    def GetAllPages(self):
        return self.pages

    def __getattr__( self, name):
        return self.tree.__getattribute__(name)

#-------------------------------------------------------------------------------
class SettingsDialog(wx.Dialog):
    def __init__(self, settings_panels, imagelist):
        wx.Dialog.__init__(self,None,-1,title='PTK Preferences',
                            style=wx.DEFAULT_DIALOG_STYLE| wx.RESIZE_BORDER,size=(720,420))
        
        #sizer to hold all controls
        vsizer = wx.BoxSizer(wx.VERTICAL)

        #create the tree book
        self.treebook = SettingsTreeBook(self, -1)
        vsizer.Add(self.treebook,1,wx.EXPAND|wx.ALL,5)

        #set up an image list to use
        self.il = imagelist
        self.treebook.SetImageList(self.il)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        vsizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)

        apply_but = wx.Button(self,wx.ID_APPLY, "Apply")
        ok_but    = wx.Button(self, wx.ID_OK, "OK")
        cancel_but= wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=wx.ID_APPLY)

        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( apply_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( ok_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( cancel_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        vsizer.Add(butsizer,0, wx.ALIGN_RIGHT)

        #Add pages
        for (address, panel_class, bitmap) in settings_panels:
            if panel_class is not None:
                panel = panel_class(self.treebook)
            else:
                panel = None
            self.treebook.AddPage(address, panel, bitmap )

        self.SetSizer(vsizer)
        self.Layout()

        #Load all the settings
        self.LoadSettings()

    def OnApply(self,event):
        page = self.treebook.GetCurrentPage()
        if page is not None:
            page.SaveSettings()

    def LoadSettings(self):
        """Load the settings from the config"""
        for page in self.treebook.GetAllPages():
            try:
                page.LoadSettings()
            except:
                pass

    def SaveSettings(self):
        """Save the settings to the config"""
        for page in self.treebook.GetAllPages():
            try:
                page.SaveSettings()
            except:
                pass
