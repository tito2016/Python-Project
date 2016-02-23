"""
Type view panel for strings and unicode strings
"""
import wx
from viewer import TypeView

class StringView(TypeView):
    """Simple view for strings and unicode etc"""
    def __init__(self,viewer,oname,eng):
        TypeView.__init__(self,viewer,oname,eng)
        self.type = None #is this a string or unicode - value set on Refresh

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self.tctrl = wx.TextCtrl(self, -1,'',style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        sizer.Add(self.tctrl,1,wx.EXPAND|wx.ALL,0)
    
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.apply   = wx.Button(self, -1, "Apply")
        self.revert = wx.Button(self, -1, "Revert")
        self.Bind(wx.EVT_BUTTON, self.OnApply, self.apply)
        self.Bind(wx.EVT_BUTTON, self.OnRevert, self.revert)
        butsizer.Add(self.apply)
        butsizer.Add(self.revert)

        sizer.Add(butsizer,0,wx.ALL|wx.ALIGN_RIGHT,2)
        self.RefreshView()

    def RefreshView(self):
        """Sets the text"""
        #get the contents of the object
        if self.disabled is False:
            t=self.eng.evaluate(self.oname)
            self.type = self.eng.evaluate('type('+self.oname+').__name__')
            self.tctrl.SetValue(t)

    def DisableView(self):
        """Overloaded disable method"""
        #prevent the table from trying to use the engine
        self.disabled = True
        self.tctrl.Disable()
        self.apply.Disable()
        self.revert.Disable()
        self.Disable()

    def EnableView(self,eng):
        """Overloaded EnableView method"""
        self.eng = eng
        self.disabled = False
        self.tctrl.Enable()
        self.apply.Enable()
        self.revert.Enable()
        self.Enable()

    def OnApply(self,event):
        """Store changes back to the object"""
        if self.disabled is True:
            return

        #get new value and store
        new = self.tctrl.GetValue()
        if self.type=='str':
            if type(new)==unicode:
                try:
                    new = new.encode(wx.GetDefaultPyEncoding())
                except UnicodeEncodeError:
                    pass # otherwise leave it alone 
            self.eng.execute(self.oname+'= "'+new+'"')

        else: #unicode
            self.eng.execute(self.oname+'=u"'+new+'"')
        #publish engine state change message
        self.eng.notify_change()

    def OnRevert(self,event):
        """Revert to actual value"""
        self.RefreshView()
