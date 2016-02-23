"""
A general report/info control with icon/label/value, label/value or collapsible
items.

Used for Inspector tool
"""

import  wx
from wx.lib.scrolledpanel import ScrolledPanel
from controls import WWStaticText
import iconbutton
from iconbutton import EvtIconClick,EvtIconToggle,EVT_ICON_CLICK,EVT_ICON_TOGGLE

#-------------------------------------------------------------------------------
ITEM_NOICON     = 0
ITEM_STATIC     = 1
ITEM_BUTTON     = 2 
ITEM_COLLAPSE   = 3
ITEM_TOGGLE     = 4

#-------------------------------------------------------------------------------
class InfoItem(wx.Panel):
    def __init__(self,infoctrl,id,label,window,bitmap=None,orient=wx.HORIZONTAL, style=ITEM_NOICON):

        if isinstance(infoctrl, InfoCtrl) is False:
            raise Exception('Expected an InfoCtrl as parent')

        wx.Panel.__init__(self,infoctrl,id)
        self.SetBackgroundColour('white')

        #icon/spacer and style
        w = infoctrl.GetIconColWidth()
        self.style = style

        # No icon, label, and value only
        if  style==ITEM_NOICON:
            self.icon = wx.Panel( self,-1,size=(w,-1))
            self.icon.SetBackgroundColour('white')

        # static bmp, label and value
        elif style==ITEM_STATIC:
            self.icon = wx.StaticBitmap(self,-1,bitmap)

        # button icon, label and value
        elif style==ITEM_BUTTON:
            self.icon = iconbutton.BmpIcon(self,-1,bitmap)
            self.icon.SetBackgroundColour('white')
            self.icon.Bind(iconbutton.EVT_ICON_CLICK, self.OnButton)

        # collapsable item - vertical only
        elif style==ITEM_COLLAPSE:
            self.icon = iconbutton.ToggleIcon(self,-1,iconbutton.collapse.GetBitmap(),
                        iconbutton.expand.GetBitmap())
            self.icon.SetBackgroundColour('white')
            self.icon.Bind(iconbutton.EVT_ICON_TOGGLE, self.OnExpand)
            self.icon.SetToolTipString('Collapse')
            self.hidden=False
            orient = wx.VERTICAL

        #toggle icon
        elif style==ITEM_TOGGLE:
            self.icon = iconbutton.ToggleIcon(self,-1,iconbutton.radio_on.GetBitmap(),
                        iconbutton.radio_off.GetBitmap())
            self.icon.SetBackgroundColour('white')
            self.icon.Bind(iconbutton.EVT_ICON_TOGGLE, self.OnToggle)
            self.icon.SetToolTipString('Toggle')
        
        self.s_out = wx.BoxSizer(orient)
        self.s_in  = wx.BoxSizer(wx.HORIZONTAL)
        iw,ih = self.icon.GetSizeTuple()
        self.s_in.Add(self.icon,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,3+(w-iw))

        #label
        self.label = wx.StaticText(self,-1,label)
        labelfont = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
        labelfont.SetWeight(wx.BOLD)
        self.label.SetFont(labelfont)
        self.s_in.Add(self.label,0,wx.ALIGN_CENTER_VERTICAL,0)

        #add label and icon
        self.s_out.Add(self.s_in,0,wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT,3)

        #add window
        self.window = window
        self.window.Reparent(self)
        if orient == wx.VERTICAL:
            self.s_out.Add(self.window,1,wx.EXPAND|wx.LEFT|wx.RIGHT,3)
        else:
            self.s_out.Add(self.window,1,wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT,3)

        self.SetSizer(self.s_out)

    def SetIconWidth(self,w):
        """Set the icon+spacer width - called automatically by InfoCtrl"""
        #remove icon
        self.s_in.Remove(self.icon)
        #add again
        w = self.Parent.GetIconColWidth()
        iw,ih = self.icon.GetSizeTuple()
        self.s_in.Insert(0,self.icon,0,wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,5+(w-iw))

    
    def Expand(self,flag=True):
        """Expand (or collapse) the panel, flag=True to expand""" 
        if self.style != ITEM_COLLAPSE:
            raise Exception('InfoItem is not collapsable')
        #On collapse
        if flag is False:
            if self.hidden is True:
                return False
            #hide item window
            self.window.Show(flag)
            #set item proportion
            sitem = self.Parent.sizer.GetItem(self)
            sitem.SetProportion(0)
            self.icon.SetToolTipString('Expand')

        
        #On expand
        if flag is True:
            if self.hidden is False:
                return False
            #show item window
            self.window.Show(flag)
            #set item proportion
            sitem = self.Parent.sizer.GetItem(self)
            sitem.SetProportion(1)  
            self.icon.SetToolTipString('Collapse')
      
        self.hidden = not flag
        self.icon.SetState(flag)
        self.Layout()
        self.Refresh()
        self.Parent.Refresh()
        self.Parent.Layout()
        tlp = self.GetTopLevelParent()
        tlp.Layout()
        tlp.Refresh()

    def SetToolTipString(self,tip):
        """Set the tool tip string - shown when hovering over icon"""
        self.icon.SetToolTipString(tip)

    #---events------------------------------------------------------------------
    def OnExpand(self,event):
        self.Expand(self.hidden)
        self.ProcessEvent(event)

    def OnButton(self,event):
        self.ProcessEvent(event)

    def OnToggle(self,event):
        self.ProcessEvent(event)


#-------------------------------------------------------------------------------
class InfoCtrl(ScrolledPanel):
    """
    A general report/info control that can hold panels seperated by a line
    """
    def __init__(self,parent,id):    
        ScrolledPanel.__init__(self, parent, -1, style=wx.BORDER_SUNKEN)
        self.SetBackgroundColour('white')

        #the sizer to which all items are added
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        #item attributes
        self.items = []
        self.lines = []
        self.iconsize = 22

    #---------------------------------------------------------------------------
    def GetIconColWidth(self):
        return self.iconsize

    def SetIconColWidth(self,w):
        self.iconsize = w
        for item in self.items:
            item.SetIconWidth(w)
        self.Refresh()

    #---------------------------------------------------------------------------
    def AddItem(self, label, window, bitmap=None, orient=wx.HORIZONTAL,
                style=ITEM_NOICON, fill=True):
        """
        Add an item to the control
        """

        if (type(window) in [str,unicode]) and orient==wx.HORIZONTAL:
            window = wx.StaticText(self,-1,window)  
        if (type(window) in [str,unicode]) and orient==wx.VERTICAL:
            window = WWStaticText(self,-1,window)
            window.SetBackgroundColour(self.GetBackgroundColour())
        item = InfoItem(self,-1,label,window,bitmap,orient,style)

        if (fill is True) or (style==ITEM_COLLAPSE):
            prop=1
        else:
            prop=0
        self.sizer.Add(item,prop,wx.EXPAND|wx.ALL,3)
        self.items.append( item )

        #add line
        line = wx.StaticLine(self,-1,size=(-1,1))
        self.sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,3)
        self.lines.append( line )

        self.Layout()
        self.SetupScrolling()

        return item

    def RemoveItem(self,n):
        """
        Remove and destroy the item and an child windows (e.g. windows 
        managed by collapsible items
        """
        #remove item
        item = self.items.pop(n)
        item.Destroy()
        #remove line
        line = self.lines.pop(n)
        line.Destroy()
        self.Layout()
        self.SetupScrolling()

    def GetItem(self,n):
        """
        Get the nth item
        """
        return self.items[n]

    def ClearItems(self):
        """
        Clear and destroy all items
        """
        for item in self.items:
            item.Destroy()
        for line in self.lines:
            line.Destroy()
        self.items=[]
        self.lines=[]
        self.Layout()
        self.SetupScrolling()

    def CollapseAllItems(self):
        """Collapse any items with the style ITEM_COLLAPSE"""
        for item in self.items:
            if item.style==ITEM_COLLAPSE:
                item.Expand(False)

    def ExpandAllItems(self):
        """Expand any items with the style ITEM_COLLAPSE"""
        for item in self.items:
            if item.style==ITEM_COLLAPSE:
                item.Expand(True)

    

#---test function---------------------------------------------------------------
def test(): 
    f= wx.Frame(None,-1,'test')
    s= wx.BoxSizer(wx.VERTICAL) 
    f.SetSizer(s)

    ic = InfoCtrl(f,-1)
    s.Add(ic,1,wx.EXPAND|wx.ALL,0)
    f.Show()
    
    #build items
    bmp = iconbutton.close.GetBitmap()
    i1= ic.AddItem( label='No icon', window="style=ITEM_NOICON", bitmap=None,
                    orient=wx.HORIZONTAL, style=ITEM_NOICON, fill=False)

    i2= ic.AddItem( label='Static icon', window="style=ITEM_STATIC", bitmap=bmp,
                    orient=wx.HORIZONTAL, style=ITEM_STATIC, fill=False)

    i3= ic.AddItem( label='Button icon', window="style=ITEM_BUTTON", bitmap=bmp,
                    orient=wx.HORIZONTAL, style=ITEM_BUTTON, fill=False)

    i4= ic.AddItem( label='Collapsible item', window="style=ITEM_COLLAPSE",
                    orient=wx.VERTICAL, style=ITEM_COLLAPSE)

    i5= ic.AddItem( label='Toggle item', window="style=ITEM_TOGGLE",
                    orient=wx.HORIZONTAL, style=ITEM_TOGGLE, fill=False)

    i6= ic.AddItem( label='Collapsible item', window="style=ITEM_COLLAPSE",
                    orient=wx.VERTICAL, style=ITEM_COLLAPSE)
    return f,ic
