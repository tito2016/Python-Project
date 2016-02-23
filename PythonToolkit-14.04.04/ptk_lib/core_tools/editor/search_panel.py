"""
This contains the editor search and replace pane

SearchPanel - the panel class
"""
import wx

#---Search/replace panel--------------------------------------------------------
class SearchPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        self.notebook = parent.notebook

        #add the find elements to a sizer
        text1   = wx.StaticText(self, -1, 'Find:', size=(100,-1))
        self.findstr = wx.TextCtrl(self,-1, size=(200,-1), style=wx.TE_PROCESS_ENTER)
        self.findbut = wx.Button(self, -1, "Find")
        self.Bind(wx.EVT_BUTTON, self.OnFind, self.findbut)

        sfind = wx.BoxSizer(wx.HORIZONTAL)
        sfind.Add(text1, 0, wx.ALIGN_CENTER)
        sfind.Add(self.findstr, 0, wx.ALIGN_CENTER)
        sfind.Add(self.findbut, 0, wx.ALIGN_CENTER)

        #add the replace elements to a sizer
        text2   = wx.StaticText(self, -1, 'Replace with:', size=(100,-1))
        self.repstr = wx.TextCtrl(self,-1, size=(200,-1), style=wx.TE_PROCESS_ENTER)
        self.repbut = wx.Button(self, -1, "Replace")
        self.Bind(wx.EVT_BUTTON, self.OnReplace, self.repbut)
        self.repallbut = wx.Button(self, -1, "Replace All")
        self.Bind(wx.EVT_BUTTON, self.OnReplaceAll, self.repallbut)

        srep = wx.BoxSizer(wx.HORIZONTAL)
        srep.Add(text2, 0, wx.ALIGN_CENTER)
        srep.Add(self.repstr, 0, wx.ALIGN_CENTER)
        srep.Add(self.repbut, 0, wx.ALIGN_CENTER)
        srep.Add(self.repallbut, 0, wx.ALIGN_CENTER)

        #add the find and replace sizers to another sizer
        sizer1 = wx.BoxSizer(wx.VERTICAL)
        sizer1.Add(sfind,1,wx.EXPAND,0)
        sizer1.Add(srep,1,wx.EXPAND,0)

        #search options
        self.matchcase = wx.CheckBox(self, -1, "Match case")
        self.wholeword = wx.CheckBox(self, -1, "Match whole word only")
        self.backwards = wx.CheckBox(self, -1, "Search Backwards")
        
        scbox = wx.BoxSizer(wx.VERTICAL)
        scbox.Add(self.matchcase,0,wx.NORTH,1)
        scbox.Add(self.wholeword,0,wx.NORTH,1)
        scbox.Add(self.backwards,0,wx.NORTH,1)

        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(sizer1,0,wx.ALIGN_CENTER|wx.WEST,20)
        sizer2.Add(scbox ,0,wx.ALIGN_CENTER|wx.WEST,20)
        self.SetSizer(sizer2)

    def OnFind(self,event):
        """Searchs the current notebook page for the string in the find box"""
        #set the search flags
        flags=0
        if self.matchcase.IsChecked():
            flags = flags | wx.stc.STC_FIND_MATCHCASE
        if self.wholeword.IsChecked():
            flags = flags | wx.stc.STC_FIND_WHOLEWORD
        #get the string
        stext= self.findstr.GetRange(0,-1)
        #search backwards
        back = self.backwards.IsChecked() 
        #do the search
        found = self.notebook.Find(stext,back,flags)
        #check for not found
        if found is False:
            wx.MessageBox('String: '+stext+' not found','Find')

    def OnReplace(self,event):
        """
        Searchs the current notebook page for the string in the find box, when
        found, it replaces it with the string in the replace box
        """
        #set the search flags
        flags=0
        if self.matchcase.IsChecked():
            flags = flags | wx.stc.STC_FIND_MATCHCASE
        if self.wholeword.IsChecked():
            flags = flags | wx.stc.STC_FIND_WHOLEWORD
        #get the string
        stext= self.findstr.GetRange(0,-1)
        rtext= self.repstr.GetRange(0,-1) #the replace string
        #search backwards
        back = self.backwards.IsChecked() 
        #do the search
        found = self.notebook.Replace(stext,rtext,back,flags)
        #check for not found
        if found is False:
            wx.MessageBox('String: '+stext+' not found','Replace')

        
    def OnReplaceAll(self,event):
        """
        Searchs the current notebook page for the string in the find box, when
        found, it replaces it with the string in the replace box
        """
        #set the search flags
        flags=0
        if self.matchcase.IsChecked():
            flags = flags | wx.stc.STC_FIND_MATCHCASE
        if self.wholeword.IsChecked():
            flags = flags | wx.stc.STC_FIND_WHOLEWORD
        #get the string
        stext= self.findstr.GetRange(0,-1)
        rtext= self.repstr.GetRange(0,-1) #the replace string
        #search backwards
        back = self.backwards.IsChecked() 
        #do the search
        found = self.notebook.ReplaceAll(stext,rtext,back,flags)      

    def SetFocus(self):
        """
        Set the focus to the find entry box.
        """
        self.findstr.SetFocus()