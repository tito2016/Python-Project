"""
Controls module

Various custom controls that can be used in different places.

IntValidator -  A validator for text controls that only allows ints.
AutoSizeListCtrl -  Alist control with the auto width mixin already added.
PanelList   -   scrolling list of items where each item is a panel
LabelBitmap -   static bmp with a label.
"""
import wx
from wx.lib.scrolledpanel import ScrolledPanel
import  wx.lib.mixins.listctrl  as  listmix
import string


__all__ = ['WWStaticText', 'ScrolledText', 'IntValidator' ,'AutoSizeListCtrl', 'EditListCtrl','LabelBitmap', 'BmpBook']

#---WWStaticText----------------------------------------------------------------
# A static text control which automatically word wraps the contents when resized
# it is a panel containing a normal static text
class WWStaticText(wx.Panel):
    """ A static text control with automatic word wrapping """
    def __init__(self,parent,id=-1,label=''):
        wx.Panel.__init__(self,parent,id)
        self.label = label
        self.text = wx.StaticText(self,-1,label)
        self.Bind(wx.EVT_SIZE, self.OnSize, self)

    def OnSize(self,event):
        w,h = self.GetSizeTuple()
        self.text.SetLabel(self.label)
        self.text.Wrap(w)
        event.Skip()
    
    def SetLabel(self,label):
        w,h = self.GetSizeTuple()
        self.text.SetLabel(label)
        self.label=label
        self.text.Wrap(w)

    def SetFont(self, font):
        return self.text.SetFont(font)

    def GetFont(self):
        return self.text.GetFont()

#---ScrollText------------------------------------------------------------------
# A static text control with automatic word wrapping and scrolling
class ScrolledText(ScrolledPanel):
    def __init__(self,parent,id,label,size=wx.DefaultSize,pos=wx.DefaultPosition,style=wx.BORDER_NONE):
        ScrolledPanel.__init__(self,parent,id,size=size,pos=pos,style=style)

        self.label = label

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.StaticText(self,-1,label)
        sizer.Add(self.text,1,wx.EXPAND)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_SIZE, self.OnSize, self)
        self.SetupScrolling()

    def OnSize(self,event):
        w,h = self.GetSizeTuple()
        self.text.SetLabel(self.label)
        sw = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.text.Wrap(w-sw-4)
        self.Layout()
        event.Skip()
    
    def SetLabel(self,label):
        w,h = self.GetSizeTuple()
        self.text.SetLabel(label)
        self.label=label
        sw = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.text.Wrap(w-sw-4)
        self.Layout()


#---Validators------------------------------------------------------------------
class IntValidator(wx.PyValidator):
    def __init__(self):
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return IntValidator()

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()
        for x in val:
            if x not in string.digits:
                return False
        return True

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return
        if chr(key) in string.digits:
            event.Skip()
            return
        if not wx.Validator_IsSilent():
            wx.Bell()
        return

#---AutoSizeListCtrl------------------------------------------------------------
# This is a list control with the autowidth mixin applied so you don't have to.
#-------------------------------------------------------------------------------
class AutoSizeListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

#---EditListCtrl----------------------------------------------------------------
# A list control with editable text fields
#-------------------------------------------------------------------------------
class EditListCtrl(wx.ListCtrl,
                   listmix.ListCtrlAutoWidthMixin,
                   listmix.TextEditMixin):

    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)

        self.edit_cols = [] #list of columns that are editable.
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.TextEditMixin.__init__(self)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnEdit)

    def SetEditableColumns(self, edit_cols=[]):
        """
        Set the columns that can be edited.
        """
        self.edit_cols = edit_cols

    def GetEditableColumns(self):
        """
        Get the columns that can be edited
        """
        return self.edit_cols

    def SetColumnEditable(self, col, flag=True):
        """
        Set a column to be editable
        """
        if (flag is False):
            if col in self.edit_cols:
                n = self.edit_cols.index(col)
                self.edit_cols.pop(n)
            return
        if col not in self.edit_cols:
            self.edit_cols.append(col)
            self.edit_cols.sort()
        

    def OnEdit(self,evt):
        if evt.m_col not in self.edit_cols:
            evt.Veto()
            return
        evt.Skip()

#-------------------------------------------------------------------------------
# A static bitmap class with a centered label plus the ablitity to disable with
# a greyscale version of the bmp, and a 'selected' version with the caption 
# highlighted.
#-------------------------------------------------------------------------------
class LabelBitmap(wx.Panel):
    """
    A static bitmap with centered label and some extras:

        Enable/Disable - changes bmp to greyscale/full colour as well as well as
                        disabling events
        Select/DeSelect - highlights the label.
    """
    def __init__(self,parent,id=-1,bmp=wx.NullBitmap,label='',pos=(-1,-1),size=(-1,-1)):
        #use bmp size to determine size if none specified
        bw,bh = bmp.GetSize().Get()
        self.bsize = (bw,bh)
        if size[0] == -1:
            w = bw*3
        else:
            w = size[0]
        if size[1] == -1:
            h = bh*2
        else:
            h = size[1]
        self.size=(w,h)

        wx.Panel.__init__(self,parent,id,pos,size=self.size)
        col = parent.GetBackgroundColour()
        self.SetBackgroundColour(col)
        
        #store the bmps
        self.enabled = True
        self.bmp = bmp
        self.disabled_bmp = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()

        #selection
        self.selected = False
        self.bgcol = col

        #store the label
        self.label = label

        #font to use
        self.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD, False))

        self.Bind(wx.EVT_PAINT, self.OnPaint)
    #---API---------------------------------------------------------------------
    def Enable(self,enable=True):
        """Show full colour bmp and call wx.window.Enable"""
        self.enabled = enable
        wx.Panel.Enable(self,enable)
        self.Refresh()
        
    def Disable(self):
        """Show a grayscale version of the bmp and call wx.window.Disable"""
        self.enabled = False
        wx.Panel.Disable(self)
        self.Refresh()

    def Select(self,select=True):
        """Show a highlighted version"""
        self.selected = select
        self.Refresh()

    def UnSelect(self):
        """Show the normal version, without selection highlight"""
        self.selected = False
        self.Refresh()


    #---events------------------------------------------------------------------
    def OnPaint(self,event):
        dc = wx.PaintDC(self)

        #set text/line/fill colours
        if self.selected:
            col = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
            dc.SetTextForeground(col)
            col = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        else:
            col = wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNTEXT)
            dc.SetTextForeground(col)
            col=self.GetBackgroundColour()
        dc.SetPen(wx.Pen(col))
        dc.SetBrush(wx.Brush(col))

        #the bmp
        x = (self.size[0]/2) - (self.bsize[0]/2)
        y = 5
    
        if self.enabled:
            dc.DrawBitmap(self.bmp, x, y, True)
        else:
            dc.DrawBitmap(self.disabled_bmp, x, y, True)

        #the label
        dc.SetFont(self.Font)
        w, h = dc.GetTextExtent(str(self.label))
        x = (self.size[0]/2) - w/2
        y = y+self.bsize[1] + 5
        dc.DrawRoundedRectangle(x-5,y-2,w+10,h+4,3)
        dc.DrawText(self.label, x, y)

#-------------------------------------------------------------------------------
# A book control similiar to a list book but with more control over the icons 
# used. Each page adds a LabelBitmap to a panel list which controls the display
# of the page.
#-------------------------------------------------------------------------------
class BmpBook(wx.Panel):
    def __init__(self,parent,id=-1,pos=(-1,-1),size=(-1,-1),orient=wx.HORIZONTAL,
                style=wx.TAB_TRAVERSAL|wx.NO_BORDER):
        """
        Create a new BmpBook - a book control using label bitmaps
        """
        wx.Panel.__init__(self,parent,id,pos,size,style)

        #main sizer
        if orient==wx.HORIZONTAL:
            o = wx.VERTICAL
            w,h = size[0],74
        elif orient==wx.VERTICAL:
            o = wx.HORIZONTAL
            w,h = 122,size[1]
        else:
            o = orient
            w,h = -1,-1

        self.box  = wx.BoxSizer(o)
        self.SetSizer(self.box)

        #panel list for the item LabelBmp icons
        self.pl = PanelList(self,size=(w,h),orient=orient)
        self.box.Add(self.pl,0,wx.EXPAND,0)

        #the sizer to contain the item panels
        self.psizer = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.psizer,1,wx.EXPAND,0)

        #book internals
        self.active = None
        self.pages = [] #lsit of pages added (panel,labelbmp)
    
    def AddPage(self,page,bmp,label):
        """Add a page to the book"""
        lb = LabelBitmap(self.pl,bmp=bmp,label=label,size=(96,-1))
        self.pl.AddItem(lb)
        lb.page=page
        lb.Bind(wx.EVT_LEFT_DOWN,self.OnPageSelect)
        self.pages.append(lb)

        #add to the panel sizer
        self.psizer.Add(page,1,wx.EXPAND,0)
        page.Hide()

        #select if first page
        if len(self.pages)==1:
            self.active = lb
            lb.Select()
            page.Show()
            self.psizer.Layout()

    def OnPageSelect(self,event):
        win = event.GetEventObject()
        if self.active==win:
            return
        #unselect previous
        if self.active is not None:
            self.active.page.Hide()
            self.active.UnSelect()
        #select new
        self.active = win
        win.page.Show()
        win.Select()
        self.psizer.Layout()
