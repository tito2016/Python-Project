"""
ConsoleSettings - console option panels.
"""

import pickle       #for load/save of engine names and types
import __future__   #for python __future__ feature flags

import wx
from ptk_lib import controls

import console_dialogs

#-------------------------------------------------------------------------------
class ConsoleSettingsPanel(wx.Panel):
    def __init__    (self,parent):
        wx.Panel.__init__(self,parent,-1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
        ##display settings
        dispbox = wx.StaticBox(self, -1, "Display settings:")
        boldfont = dispbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        dispbox.SetFont(boldfont)
        dispsizer1 = wx.StaticBoxSizer(dispbox, wx.VERTICAL)
        sizer.Add(dispsizer1,0,wx.EXPAND|wx.ALL,5)

        #display line numbers
        self.cblinenums = wx.CheckBox(self, -1, "Show line numbers")
        dispsizer1.Add(self.cblinenums, 0, wx.EXPAND|wx.ALL, 10)
        #auto display autocompletes
        self.cbautocomps = wx.CheckBox(self, -1, "Auto show completions")
        dispsizer1.Add(self.cbautocomps, 0,wx.EXPAND|wx.ALL, 10)
        #auto display calltips
        self.cbcalltips = wx.CheckBox(self, -1, "Auto show calltips")
        dispsizer1.Add(self.cbcalltips, 0, wx.EXPAND|wx.ALL, 10)
        #use syntax highlighting
        self.syntax = wx.CheckBox(self, -1, "Use syntax highlighting")
        dispsizer1.Add(self.syntax, 0, wx.EXPAND|wx.ALL, 10)

    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        app = wx.GetApp()
        cfg = app.GetConfig()
        cfg.SetPath("Console//")

        #show line numbers
        flag = cfg.ReadBool("show_linenumbers",False)
        self.cblinenums.SetValue(flag)

        #show autocomps
        flag = cfg.ReadBool("show_autocomps",True)
        self.cbautocomps.SetValue(flag)

        #show calltips
        flag = cfg.ReadBool("show_calltips",True)
        self.cbcalltips.SetValue(flag)

        #use syntax highlighting
        flag = cfg.ReadBool("use_syntax_highlight",True)
        self.syntax.SetValue(flag)


    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        app = wx.GetApp()
        cfg = app.GetConfig()
        cfg.SetPath("Console//")
        
        #show line numbers
        flag = self.cblinenums.GetValue()
        cfg.WriteBool("show_linenumbers",flag)

        #show autocomps
        flag = self.cbautocomps.GetValue()
        cfg.WriteBool("show_autocomps",flag)

        #show calltips
        flag = self.cbcalltips.GetValue()
        cfg.WriteBool("show_calltips",flag)

        #use syntax highlighting
        flag = self.syntax.GetValue()
        cfg.WriteBool("use_syntax_highlight",flag)

        cfg.Flush()

        #now update all open engine consoles stc
        app = wx.GetApp()
        console = app.toolmgr.get_tool('Console')
        pages = console.get_all_engines(active=False)
        for page in pages:
            page.LoadOptions()

#-------------------------------------------------------------------------------
class AutostartPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,-1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        ##Engine options
        engbox = wx.StaticBox(self, -1, "Engines to create on startup:")
        boldfont = engbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        engbox.SetFont(boldfont)
        engsizer1 = wx.StaticBoxSizer(engbox, wx.HORIZONTAL)
        sizer.Add(engsizer1,1,wx.EXPAND|wx.ALL,5)

        #Set engines to autostart
        self.englist = controls.AutoSizeListCtrl(self, -1, style=wx.LC_REPORT | 
                wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_SINGLE_SEL)
        self.englist.InsertColumn(0, "Label")
        self.englist.InsertColumn(1, "Type")
        self.englist.SetColumnWidth(0,220)
        
        engsizer2 = wx.BoxSizer(wx.VERTICAL)
        self.addbut = wx.Button(self,-1,"Add")
        self.renamebut = wx.Button(self,-1,"Rename")
        self.rembut = wx.Button(self,-1,"Remove")
        self.clearbut = wx.Button(self,-1,"Remove All")

        self.Bind(wx.EVT_BUTTON, self.OnAddEng, self.addbut)
        self.Bind(wx.EVT_BUTTON, self.OnRenameEng, self.renamebut)
        self.Bind(wx.EVT_BUTTON, self.OnRemEng, self.rembut)
        self.Bind(wx.EVT_BUTTON, self.OnClearEng, self.clearbut)

        engsizer2.Add(self.addbut,0,wx.ALIGN_CENTER_VERTICAL)
        engsizer2.Add(self.renamebut,0,wx.ALIGN_CENTER_VERTICAL)
        engsizer2.Add(self.rembut,0,wx.ALIGN_CENTER_VERTICAL)
        engsizer2.Add(self.clearbut,0,wx.ALIGN_CENTER_VERTICAL)
        engsizer1.Add(self.englist,1,wx.EXPAND|wx.ALL,5)
        engsizer1.Add(engsizer2,0,wx.ALL,5)   

    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Console//")

        #eng list
        s = cfg.Read("auto_start_engines","")  #a list of engine name, type tuples to autostart

        try:
            self.engines = pickle.loads(str(s))
        except:
            self.engines=[("Engine-1","wxEngine")]
        
        #add to the list control
        for engname,engtype in self.engines:
            self.englist.Append((engname,engtype))

    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Console//")

        #eng list
        s = pickle.dumps(self.engines)
        cfg.Write("auto_start_engines",s)  #a list of engine name,type tuples to autostart
        cfg.Flush()    

    #---events------------------------------------------------------------------
    def OnAddEng(self,event):
        names = []
        for i in self.engines:
            names.append(i[0])            
        d= console_dialogs.EngineChoiceDialog(self,'Setup engine to autostart')
        val=d.ShowModal()
        if val==wx.ID_OK:
            engname,engtype = d.GetValue()
            self.engines.append((str(engname),str(engtype)))
            self.englist.Append((engname,engtype))
        d.Destroy()

    def OnRenameEng(self, event):
        item = self.englist.GetNextSelected(-1)
        if item==-1:
            #no selection
            return
        engname,engtype = self.engines[item]
        dlg = wx.TextEntryDialog(None, 'Rename '+engname+' to:','Rename:', '')
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        new = str(dlg.GetValue())
        dlg.Destroy()
        #check name
        for n,t in self.engines:
            if new==n:
                msg = 'An engine with that name is already configured to autostart, the engine name must be unique.'
                title='Engine name already used!'
                controls.Message(msg,title)
                return
        #store new name
        self.engines[item] = (new,engtype)
        self.englist.SetItemText(item, new)

    def OnRemEng(self,event):
        item = self.englist.GetNextSelected(-1)
        if item==-1:
            #no selection
            return
        self.engines.pop(item)
        self.englist.DeleteItem(item)

    def OnClearEng(self,event):
        self.engines = []
        self.englist.DeleteAllItems()


#-------------------------------------------------------------------------------
class EnvironmentPanel(wx.Panel):
    def __init__    (self,parent):
        wx.Panel.__init__(self,parent,-1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
 
        #Startup script
        startbox = wx.StaticBox(self, -1, "Python startup script:")
        boldfont = startbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        startbox.SetFont(boldfont)

        startsizer = wx.StaticBoxSizer(startbox, wx.VERTICAL)
        self.exec_startup = wx.CheckBox(self, -1, "Execute python startup script")
        startsizer.Add(self.exec_startup, 0, wx.EXPAND|wx.ALL, 10)

        sizer.Add(startsizer,0,wx.EXPAND|wx.ALL,5)

        #Future options
        futbox = wx.StaticBox(self, -1, "Python future features:")
        boldfont = futbox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        futbox.SetFont(boldfont)

        futsizer1 = wx.StaticBoxSizer(futbox, wx.VERTICAL)
        futsizer2 = wx.GridSizer(3, 1, 2, 2)  # rows, cols, vgap, hgap
        futsizer1.Add(futsizer2,1,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL)

        self.future_div = wx.CheckBox(self, -1, "Enable future division")
        futsizer2.Add(self.future_div, 0, wx.EXPAND|wx.ALL, 10)

        self.future_print = wx.CheckBox(self, -1, "Enable future print function")
        futsizer2.Add(self.future_print, 0, wx.EXPAND|wx.ALL, 10)

        self.future_unicode = wx.CheckBox(self, -1, "Enable future unicode literals")
        futsizer2.Add(self.future_unicode, 0, wx.EXPAND|wx.ALL, 10)

        sizer.Add(futsizer1,0,wx.EXPAND|wx.ALL,5)

    def LoadSettings(self):
        """Load the settings from the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Console//")

        #execute python startup script
        flag = cfg.ReadBool("exec_startup",True)
        self.exec_startup.SetValue(flag)

        #use future division
        flag = cfg.ReadBool("future_div",False)
        self.future_div.SetValue(flag)

        #use future print function
        flag = cfg.ReadBool("future_print",False)
        self.future_print.SetValue(flag)

        #use future unicode
        flag = cfg.ReadBool("future_unicode",False)
        self.future_unicode.SetValue(flag)


    def SaveSettings(self):
        """Save the settings to the config"""
        #get config object
        cfg = wx.GetApp().GetConfig()
        cfg.SetPath("Console//")
       
        #execute python startup script
        flag = self.exec_startup.GetValue()
        cfg.WriteBool("exec_startup",flag)

        #use future division
        flag1 = self.future_div.GetValue()
        cfg.WriteBool("future_div",flag1)

        #use future print function
        flag3 = self.future_print.GetValue()
        cfg.WriteBool("future_print",flag3)

        #use future unicode
        flag4 = self.future_unicode.GetValue()
        cfg.WriteBool("future_unicode",flag4)

        #apply to open engines
        app = wx.GetApp()
        tool = app.toolmgr.get_tool('Console')
        engines = tool.get_engine_names()
        for engname in engines:
            eng = tool.get_engine(engname)
            eng.set_compiler_flag(__future__.CO_FUTURE_DIVISION, flag1)
            eng.set_compiler_flag(__future__.CO_FUTURE_PRINT_FUNCTION, flag3)
            eng.set_compiler_flag(__future__.CO_FUTURE_UNICODE_LITERALS, flag4)

