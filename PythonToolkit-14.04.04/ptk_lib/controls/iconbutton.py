"""
A collection of icon/button controls for use in frames/dialogs without 
title bars including some simple icons.

BmpIcon     -   A clickable button (bind with EVT_LEFT_DOWN)
ToggleIcon  -   A togglable icon with True/False states and different icons
CollapsablePanel - A collapsable control using a toggle icon for control.
"""
import wx
from wx.lib.embeddedimage import PyEmbeddedImage
from wx.lib.newevent import NewEvent


#---Icons-----------------------------------------------------------------------
resize = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oBGxAFHcdeVysAAAB8"
    "SURBVDjLvZFRCsAwCEPV7f43bt1PLW4ktVCYP0VInjWq2iUnZXJY/wC8t9dLAd4bFEVFXllj"
    "lWABcrjCF+K9IbBPPTtjiLM5TxYRLUMEcB8whT/IuzNzTB69WpX2gCLzOoNi8l4GzJwzMJY+"
    "EM8+X4OtsPx27m92wd3+AXVqSwtpAdPGAAAAAElFTkSuQmCC")

close = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAGBJ"
    "REFUOI3NkkEOwCAIBFn8/5OVnkwoZbXqxb3CTAgAaJGT6BF9n8BaNWvVskZWewmgBb05wr5O"
    "BZlkBIuIgJ3RT8HgdILVpII4NltsKojwTPI5o4d6RhK6xL+57JV38gAdfjwN/ONhRQAAAABJ"
    "RU5ErkJggg==")

expand = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oCBRUpC/sWEUMAAAA9"
    "SURBVDjLY2AY1uA/MYqYKDWEiVKXMFHqHSZKw4SJ0oAl1QBGSgxgpMQLjCQHIiMTBOPTjN9K"
    "JuJS4sADAOgbBxlBsfXrAAAAAElFTkSuQmCC")

collapse = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oCBRMnAPbKmfcAAABB"
    "SURBVDjLY2AYBcMAMKJwmBj+//9HhCYmBob//yB6GbFI4jUEWTNWA6DgP9GuxqPwPyHNhAxA"
    "N4SR3ID+P8wTEgBwLg4FdgEHxgAAAABJRU5ErkJggg==")

locked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oCBRM2IJ59mi8AAACH"
    "SURBVDjLvZPBDcQwCAQHp4H03+UVAHufWCI6QixFF57Wsl7G2GxsPKnBw/qrgQApXAoXgMJ7"
    "A4VPkQADzMZmgClck1c2OhmsAs06K5qkcJtChZNu1pGoZ5CjVrFP2irB3QTZ+AdiAXnvGLR7"
    "cDzfp41zM4I1Z0ubqIrJ5R6sVAZ4NcK7n+kLNpxCGtlk0RwAAAAASUVORK5CYII=")

unlocked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oCBRM0OL8nYPsAAACJ"
    "SURBVDjLxZNLDsMgDETfgLLpKtteo/e/VA4AziZILuVXRVUtscCaAfthpBC5E4Gb8dMD7FpP"
    "4AFgOX2I5BkUgUI0QD5f68r+rYIJ0K2lU8NklpOKsL59iUExePPV3mvIwMEbhboMGpQDsPcq"
    "nM6B5WTAMSxn0oIGuaVJtBYT3+rXo1w/q/7+G0/9DjKRYBJPSwAAAABJRU5ErkJggg==")

radio_on = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oECxEKJx/xII4AAADT"
    "SURBVDjLxZPNCgIxDIS/tOoqIqIX3//lBPEiqODfbr0kMltWPXgwUEqGZJpJE7OU+cUSP9pI"
    "ndK1Y6D1E3YArsAGmFjK9x6DpYzLyF7RFigfzjxyLOUewQg4SmBgBjQVSRN5KuE+0JvAzLHO"
    "/YtjvSbu/c5VFYg/lX6lmmAtr5eBhhepYPAbswS+s7YiHJyDReirzETC7RUjv6BdHlfacewV"
    "E3lawVw03kRicnmBnUQuFrtQutaAGXD+Mr2m+5NkIgvwAJbVGB+Anfurevns79v4BFhLPl3y"
    "s16CAAAAAElFTkSuQmCC")

radio_off = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oECxEJKKRjbtwAAADM"
    "SURBVDjLxZNBC8IwDIW/tJtThohe/P9/ThAvA/XgtK2XVNIyp+DBQCkNzWvee42I8/wSjh+j"
    "sYcUQwsEXTkG4AbsgYU4fy8QxHmUhteODkCaWX2uEecLgAY4m4s5J0BXgXQvkCxiiiFV2qSK"
    "rgDRdC61iCfd/UQxmlsavVwNsPvCmThnozcvvYtQdTT52noGIFMYVZPCBatyO1Hc2ju5znbQ"
    "G46jUV6UXs5dDN3CRgFWwPXD7xU7P874moAHsKm+8QAc9byth0/+Po1PWHQ6cCjmRTEAAAAA"
    "SUVORK5CYII=")

unchecked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oECxETLWQkYIgAAABo"
    "SURBVDjLxVMxDgAhCBP0/z9WnBiuCqlhOBaNsbXQKqK9VUpbsYZvbE17AYp2+RD4OYm3QwGw"
    "n4g1+Rng5Qh8JfDXHeRr5JZmLSD4RlK2MZ0BKqEIItlPLmCvGclgbKSijAmjI/37b9x0SSou"
    "JEkuFAAAAABJRU5ErkJggg==")

checked = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAAZiS0dE"
    "AP8A/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9oECxETMuksbX0AAAC5"
    "SURBVDjLxZPRDsIwCEUvsJklOv//D/0BE2NNwRcwXdeamj3Iy7Z2wLn0logFR4JxMKZ4Mc32"
    "SyKx0KZArA/m246g3Izqm0XNkXgFcPs6g1qOaT4XXe+1FgBY4gf/NicpkQ2AADjFHrF8CNSx"
    "LuWAnMQKuQIgtY5x9efDNC+9wRNLah1HiT37SURn9q47SbWEiJfLCTpzdOp5pedE8aSZWJ7e"
    "mUatTE6xAkimOTzQLDL1HDZs6b/fxjcOfD5ZnvMCWQAAAABJRU5ErkJggg==")

#-------------------------------------------------------------------------------
EvtIconClick  , EVT_ICON_CLICK   = NewEvent()
EvtIconToggle , EVT_ICON_TOGGLE  = NewEvent()


#-------------------------------------------------------------------------------
class BmpIcon(wx.Panel):
    def __init__(self,parent,id,bitmap,pos=wx.DefaultPosition):
        """
        A simple bitmap icon control with a border drawn when hovered over
        """
        size = bitmap.GetSize()
        wx.Panel.__init__(self, parent, id,pos, size)

        self._bitmap = bitmap
        self._disabled_bitmap = bitmap
        self._hover = False

        #self.SetBackgroundColour(self.Parent.GetBackgroundColour())

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnButton)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)



    #---------------------------------------------------------------------------
    def SetBitmap(self,bitmap):
        """Set the bitmap"""
        if isinstance(bitmap,wx.Bitmap):
            self._bitmap = bitmap
            self.Refresh()
        else:
            raise ValueError('Expected a bitmap!')

    def SetBitmapDisabled(self,bitmap=None):
        """
        Set the bitmap to disbale when the icon is disabled, use None draw no 
        button.
        """
        if isinstance(bitmap,wx.Bitmap):
            self._disabled_bitmap = bitmap
            self.Refresh()
        else:
            raise ValueError('Expected a bitmap!')
    #---events------------------------------------------------------------------
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        if self.IsEnabled():
            if self._hover:
                size = self._bitmap.GetSize()
                dc.SetPen(wx.Pen('dark grey', 1, wx.SOLID))
                bg = self.Parent.GetBackgroundColour()
                dc.SetBrush(wx.Brush(bg))
                dc.DrawRectangle(0,0,size.width,size.height)
            dc.DrawBitmap(self._bitmap, 0, 0, True)
        elif self._disabled_bitmap is not None:
            dc.DrawBitmap(self._disabled_bitmap, 0, 0, True)

    def OnSize(self, event):
        self.Refresh()

    def OnEnter(self,event):
        self._hover=True
        self.Refresh()

    def OnLeave(self,event):
        self._hover=False
        self.Refresh()

    def OnButton(self,event):
        if self.IsEnabled():
            event = EvtIconClick()
            self.ProcessEvent(event)

#-------------------------------------------------------------------------------
class ToggleIcon(wx.Panel):
    def __init__(self,parent,id,bitmapTrue,bitmapFalse,pos=wx.DefaultPosition):
        if bitmapTrue.GetSize() !=bitmapFalse.GetSize():
            raise Exception('Bitmaps are different sizes!')
        size = bitmapTrue.GetSize()
        
        wx.Panel.__init__(self, parent, id,pos, size)

        self._bitmapTrue = bitmapTrue
        self._bitmapFalse = bitmapFalse
        self._disabled_bitmap = True

        self._hover = False
        self._state = True

        #self.SetBackgroundColour(self.Parent.GetBackgroundColour())

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnButton)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)

    #---------------------------------------------------------------------------
    def SetBitmapTrue(self,bitmap):
        """Set the True bitmap"""
        if isinstance(bitmap,wx.Bitmap):
            self._bitmapTrue = bitmap
            self.Refresh()
        else:
            raise ValueError('Expected a bitmap!')

    def SetBitmapFalse(self,bitmap):
        """Set the False bitmap"""
        if isinstance(bitmap,wx.Bitmap):
            self._bitmapFalse = bitmap
            self.Refresh()
        else:
            raise ValueError('Expected a bitmap!')

    def SetState(self,flag=True):
        """set the state of the toogle"""
        self._state = bool(flag)

    def GetState(self):
        """Get the state of the toogle"""
        return self._state

    def Toggle(self):
        """Switch state"""
        self._state = not self._state
        self.Refresh()

    #---events------------------------------------------------------------------
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        if self.IsEnabled():
            if self._hover:
                size = self._bitmapTrue.GetSize()
                dc.SetPen(wx.Pen('dark grey', 1, wx.SOLID))
                bg = self.Parent.GetBackgroundColour()
                dc.SetBrush(wx.Brush(bg))
                dc.DrawRectangle(0,0,size.width,size.height)
            if self._state is True:
                dc.DrawBitmap(self._bitmapTrue, 0, 0, True)
            else:
                dc.DrawBitmap(self._bitmapFalse, 0, 0, True)
        elif self._disabled_bitmap is not False:
            if self._state is True:
                dc.DrawBitmap(self._bitmapTrue, 0, 0, True)
            else:
                dc.DrawBitmap(self._bitmapFalse, 0, 0, True)

    def OnSize(self, event):
        self.Refresh()

    def OnEnter(self,event):
        self._hover=True
        self.Refresh()

    def OnLeave(self,event):
        self._hover=False
        self.Refresh()

    def OnButton(self,event):
        if self.IsEnabled():
            self.Toggle()
            event = EvtIconToggle(state=self._state)
            self.ProcessEvent(event)

#-------------------------------------------------------------------------------
class CollapsablePanel(wx.Panel):
    def __init__(self,parent,id,label,window=None,size=wx.DefaultSize,pos=wx.DefaultPosition,
                    style=wx.TAB_TRAVERSAL|wx.NO_BORDER):
        """
        A collapsible panel with a text label. window can be either None or a 
        wxWindow instance. 
        An icon controls the whether the control is displayed.
        """
        wx.Panel.__init__(self,parent,id,pos,size,style=style)

        #hidden flag
        self.hidden       = False

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        #button and label go in seperate sizer
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(sizer2,0,wx.EXPAND)

        #add collapse button
        self.but =  ToggleIcon(self,-1,collapse.GetBitmap(),
                        expand.GetBitmap())
        sizer2.Add(self.but,0,wx.ALIGN_CENTER,0)
        self.but.Bind(EVT_ICON_TOGGLE, self.OnButton)

        #add the label
        self.label = wx.StaticText(self,-1,label)
        sizer2.Add(self.label,0,wx.LEFT,5)
        labelfont = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
        labelfont.SetWeight(wx.BOLD)
        self.label.SetFont(labelfont)

        #create a panel
        if window is None:
            self.window = wx.Panel(self,-1)
        else:
            self.window = window
            window.Reparent(self)

        self.sizer.Add(self.window,1,wx.EXPAND|wx.ALL,5)
        self.Collapse()

    #---interfaces--------------------------------------------------------------
    def GetWindow(self):
        """Get the window managed by this control"""
        return self.window

    def SetBackgroundColour(self,colour):
        self.but.SetBackgroundColour(colour)
        wx.Panel.SetBackgroundColour(self,colour)

    def SetLabelFont(self,font):
        """Set the label font"""
        self.label.SetFont(font)

    def Expand(self,flag=True):
        """Expand (or collapse) the panel, flag=True to expand"""
        self.window.Show(flag)
        self.hidden = not flag
        self.but.SetState(flag)
        self.Layout()
        self.Refresh()
        self.Parent.Refresh()
        self.Parent.Layout()
        tlp = self.GetTopLevelParent()
        tlp.Layout()
        tlp.Refresh()

    def Collapse(self):
        """Collapse the panel"""
        self.Expand(False)

    #---events------------------------------------------------------------------
    def OnButton(self,event):
        self.Expand(self.hidden)

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def test(): 
    f= wx.Frame(None,-1,'test')
    s = wx.BoxSizer(wx.VERTICAL)
    f.SetSizer(s)

    s2= wx.BoxSizer(wx.HORIZONTAL) 
    s.Add(s2,0,wx.EXPAND)

    b1 = BmpIcon(f,-1,close.GetBitmap())
    s2.Add(b1,0,wx.ALL,5)
    b2 = BmpIcon(f,-1,resize.GetBitmap())
    s2.Add(b2,0,wx.ALL,5)
    b3 = BmpIcon(f,-1,collapse.GetBitmap())
    s2.Add(b3,0,wx.ALL,5)
    b3.Disable()

    t1 = ToggleIcon(f,-1,collapse.GetBitmap(),expand.GetBitmap())
    s2.Add(t1,0,wx.ALL,5) 
    t2 = ToggleIcon(f,-1,locked.GetBitmap(),unlocked.GetBitmap())
    s2.Add(t2,0,wx.ALL,5) 

    p = CollapsablePanel(f,-1,'Title:')
    c = wx.StaticText(p.GetWindow(),-1,"testing adding a control")
    s.Add(p,0,wx.EXPAND)

    f.Show()
    return f
