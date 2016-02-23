import wx
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib import buttons

from ptk_lib.resources import ptk_icons
from ptk_lib import controls
from ptk_lib.controls import infoctrl

#-------------------------------------------------------------------------------
class ToolManagerPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,-1)

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)

        #static box
        box = wx.StaticBox(self, -1, "Enable/Disable available Tools:")
        boldfont = box.GetFont()
        boldfont.SetWeight(wx.BOLD)
        box.SetFont(boldfont)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(bsizer,1,wx.EXPAND|wx.ALL,5)

        #tool list
        self.toollist = infoctrl.InfoCtrl(self,-1)
        self.toollist.SetIconColWidth(52)
        bsizer.Add(self.toollist,1,wx.EXPAND|wx.ALL,10)

        #add check box to show/hide core tools
        self.hide_core = wx.CheckBox(self,-1,'Hide core tools')
        self.hide_core.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        bsizer.Add(self.hide_core,0,wx.EXPAND|wx.ALL,5)

        #add note 
        note = controls.WWStaticText(self,-1,'Note: Tools will only be disabled after the program is restarted')
        bsizer.Add(note,0,wx.EXPAND|wx.ALL,5)

        self.SetSizer(sizer)

        #update list
        self.Update(True)

    def OnCheck(self,event):
        self.Update(self.hide_core.GetValue())

    def LoadSettings(self):
        #required by settings dialog
        self.toollist.Update(self.hide_core.GetValue())

    def SaveSettings(self):
        #required by setting dialog
        pass

    def Update(self, hide_core=False):
        self.toollist.Freeze()
        #clear the list
        self.toollist.ClearItems()
        #repopulate
        toolmgr = wx.GetApp().toolmgr
        avail = toolmgr.find_available_tools()
        tools = zip( avail.keys(), avail.values() )
        tools.sort()
        self.items = {}
        for name,tool in tools:
            if (tool.core is False) or (hide_core is False):
                
                #set icon
                if tool.icon is None:
                    bmp = ptk_icons.ptkicon32.GetBitmap()
                else:
                    bmp = tool.icon.GetBitmap()
                if toolmgr.is_loaded(tool.name) is False:
                    img = bmp.ConvertToImage()
                    img = img.ConvertToGreyscale()
                    bmp = img.ConvertToBitmap()
                win = ToolItem( self.toollist, tool)
                i= self.toollist.AddItem( label=tool.name, window=win, bitmap=bmp,
                    orient=wx.HORIZONTAL, style=infoctrl.ITEM_STATIC, fill=False)
                self.items[tool.name] = i
        self.toollist.Thaw() 

    def EnableTool(self, toolname, enable=True):
        item = self.items.get(toolname, None)
        if item is None:
            return
        item.icon.Enable(enable)


#-------------------------------------------------------------------------------
class ToolItem(wx.Panel):
    def __init__(self,parent,tool):
        """
        Panel displaying tool information for use inside a InfoCtrl
        """
        wx.Panel.__init__(self,parent,style=wx.NO_BORDER,size=(300,-1))
        
        #store references
        self.tool = tool
        self.toolmgr = wx.GetApp().toolmgr

        #set the background colour
        self.SetBackgroundColour('WHITE')
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(hbox)

        #more info button
        hbox.AddStretchSpacer()
        self.info = buttons.GenButton(self, -1, 'Details', style=wx.BORDER_NONE)
        font = self.info.GetFont()
        font.SetUnderlined( True)
        self.info.SetFont(font)

        #self.info = wx.Button(self, -1, 'Info...')
        self.Bind(wx.EVT_BUTTON, self.OnInfo)
        hbox.Add(self.info,0,wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL,5)

        #enable tool checkbox
        self.cb = wx.CheckBox(self, -1, 'Enable: ',style=wx.ALIGN_RIGHT)
        hbox.Add(self.cb,0,wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL,5)
        self.cb.SetValue(self.toolmgr.is_loaded(self.tool.name))
        if self.tool.core:
            self.cb.Disable()
        self.Bind(wx.EVT_CHECKBOX, self.OnEnable)

    def OnEnable(self,event):
        #start/stop tool
        if event.IsChecked():
            if self.toolmgr.is_loaded(self.tool.name) is False:
                self.toolmgr.start_tool(self.tool.name)
        else:
            self.toolmgr.stop_tool(self.tool.name)

        #set icon
        if self.tool.icon is None:
            bmp = ptk_icons.ptkicon32.GetBitmap()
        else:
            bmp = self.tool.icon.GetBitmap()
        if self.toolmgr.is_loaded(self.tool.name) is False:
            img = bmp.ConvertToImage()
            img = img.ConvertToGreyscale()
            bmp = img.ConvertToBitmap()
        self.Parent.icon.SetBitmap(bmp)

    def OnInfo(self,event):
        d = ToolInfoDialog(self, self.tool)
        d.ShowModal()
        d.Destroy()

#-------------------------------------------------------------------------------
class ToolInfoDialog(wx.Dialog):
    def __init__(self, parent, tool):
        wx.Dialog.__init__(self,parent,-1,title='Tool Info',
                            style=wx.DEFAULT_DIALOG_STYLE,size=(320,200))

        #sizer to hold all controls
        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vsizer)

        #hsizer to hold icon, name, author, version
        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vsizer.Add( hbox, 0, wx.EXPAND|wx.ALL, 5)

        #add the icon
        if tool.icon is None:
            bmp = ptk_icons.ptkicon32.GetBitmap()
        else:
            bmp = tool.icon.GetBitmap()
        self.icon = wx.StaticBitmap(self, -1, bmp)
        hbox.Add(self.icon,0,wx.ALL|wx.ALIGN_CENTER_VERTICAL,5)
    
        grid = wx.FlexGridSizer(3,2) #name,author,version
        grid.AddGrowableCol(1)
        hbox.Add(grid,1,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,5)

        #add the tool name
        n1 = wx.StaticText(self, -1, 'Name: ')  
        boldfont = n1.GetFont()
        boldfont.SetWeight(wx.BOLD)
        boldfont.SetPointSize(9)
        n1.SetFont(boldfont)
        n2 = wx.StaticText(self, -1, tool.name)  
        grid.Add(n1,0,wx.RIGHT,5)
        grid.Add(n2,1,wx.EXPAND,0)

        #add the author
        a1 = wx.StaticText(self, -1, 'Author: ')  
        a1.SetFont(boldfont)
        a2 = wx.StaticText(self, -1, tool.author)  
        grid.Add(a1,0,wx.RIGHT,5)
        grid.Add(a2,1,wx.EXPAND,0)

        #add the version
        v1 = wx.StaticText(self, -1, 'Version: ') 
        v1.SetFont(boldfont)
        v2 = wx.StaticText(self, -1, str(tool.version))
        grid.Add(v1,0,wx.RIGHT,5)
        grid.Add(v2,1,wx.EXPAND,0)

        #add the description
        d1 = wx.StaticText(self, -1, 'Description: ')
        d1.SetFont(boldfont)
        d2 = controls.WWStaticText(self, -1, tool.descrip)
        vsizer.Add(d1,0,wx.LEFT|wx.RIGHT|wx.BOTTOM,10)
        vsizer.Add(d2,1,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,10)

        #create static line and OK button
        line = wx.StaticLine(self,-1)
        vsizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)
        ok_but    = wx.Button(self, wx.ID_OK, "OK")
        vsizer.Add( ok_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
