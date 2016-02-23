import wx
import wx.lib.buttons as buttons

import time

ITEM_DROPDOWN = 8

class ToolPanel(wx.PyPanel):
    """
    A replacement toolbar class:
        -   Consistant look and feel and avoid issues with seperators on MacOs 
            Lion
        -   Dropdown menu buttons
        -   Allow the toolbar to use the main status bar even when in a pane, 
            via the SetStatusBar method.
    """
    def __init__(self, parent, id):
        wx.PyPanel.__init__(self, parent, id)

        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

        self._bgcol = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
        self.SetBackgroundColour(self._bgcol)

        self.statusbar = None
        self.tool_size = (16,16)
        self.SetToolBitmapSize((16,16))

    def AcceptsFocus(self):
        """ 
        Overloaded base class method
        """
        return False

    def SetStatusBar(self, statusbar):
        """
        Set the status bar to display help strings
        """
        self.statusbar = statusbar

    def AddTool( self, id, bitmap, kind=wx.ITEM_NORMAL, 
                shortHelp='', longHelp=''):
        """
        Add a tool, returns id
        """
        #generate an id if needed
        if id == wx.ID_ANY:
            id = wx.NewId()

        #create the tool button
        if kind == wx.ITEM_NORMAL:
            #normal button
            b = TPButtonItem(self, id, bitmap)

        elif kind == wx.ITEM_CHECK:
            #toggle button
            b = TPToggleItem(self, id, bitmap)

        elif kind == wx.ITEM_SEPARATOR:
            #seperator
            return self.AddSeparator()

        elif kind == ITEM_DROPDOWN:
            b = TPDropDown(self, id, bitmap)

        else:
            #other
            raise Exception('Unknown or not implemented tool kind')

        #set help tips
        b.SetShortHelp(shortHelp)
        b.SetLongHelp(longHelp)
        self._sizer.Add(b, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Layout()
        self.Realize()
        return id

    def AddSeparator(self):
        """
        Add a seperator to the toolpanel
        """
        line = TPSeperator(self, -1)
        self._sizer.Add(line, 0, wx.EXPAND, 0)
        self.Realize()

    def AddStaticLabel(self, text):
        """
        Add a static text label
        """
        text = TPStaticText(self, -1, text)
        self._sizer.Add(text, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Realize()

    def AddControl(self, control):
        """
        Add a control to the tool panel (the controls parent should be the 
        ToolPanel to which it will be added.
        """
        if control.Parent is not self:
            contrl.Reparent(self)
        self._sizer.Add(control, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.Realize()

    def ToggleTool(self, id, flag=True):
        """
        Toggle a tool state.
        """
        if isinstance(flag, bool) is False:
            raise ValueError('Expected a boolean for flag argument')

        #get the tool
        b = self.GetTool(id)
        try:
            b.SetToggle(flag)
        except:
            raise Exception('Not a toggle tool!')
            
    def EnableTool( self, id, flag=True ):
        """
        Enable a tool
        """
        if isinstance(flag, bool) is False:
            raise ValueError('Expected a boolean for flag argument')

        #get the tool
        b = self.GetTool(id)
        res = b.Enable(flag)
        return res
    
    def DisableTool( self, id ):
        """
        Disable a tool
        """
        return self.EnableTool( id, False)
        
    def SetToolBitmap( self, id, bmp):
        """
        Set tool bitmap
        """
        #get the tool
        b = self.GetTool(id)
        try:
            b.SetBitmap(bmp)
        except:
            raise Exception('Not a bitmap tool!')
            
    def SetToolShortHelp(self, id, shortHelp=''):
        """
        Set the tools short help string
        """
        #get the tool
        b = self.GetTool(id)
        b.SetShortHelp(shortHelp)
        
    def SetToolLongHelp(self, id, longHelp=''):
        """
        Set the tools long help string
        """
        #get the tool
        b = self.GetTool(id)
        b.SetLongHelp( longHelp)
        
    #---internals---------------------------------------------------------------
    def GetTool(self, id):
        children = self.GetChildren()
        for c in children:
            if c.GetId() == id:
                return c
        raise Exception('No tool with id '+str(id))
        
    def IsTool(self, id):
        """ Is the id given a tool """
        children = self.GetChildren()
        for c in children:
            if c.GetId() == id:
                return True
        return False

    def SetToolBitmapSize( self, size=(16,16)):
        """Set the tool size"""
        self.tool_size = size

    def GetToolBitmapSize( self):
        return self.tool_size

    def GetToolHeight( self):
        """ Get the tool height """
        #bmp size + 10
        return self.tool_size[1] + 10

    def Realize(self):
        self.SetSize( self.GetBestSize())

#-------------------------------------------------------------------------------
class TPToolItem(wx.PyControl):
    """
    Base class for toolbar tools
    """
    def __init__(self, parent, id=-1, shortHelp='', longHelp=''):

        if isinstance( parent, ToolPanel) is False:
            raise ValueError('Expected a ToolPanel parent instance')

        wx.PyControl.__init__(self, parent, id, style=wx.BORDER_NONE)

        #set tool height according to the parent toolbars bitmap size
        th = self.Parent.GetToolHeight()
        size = (-1, th)
        self.SetSize( size )
        self.SetMinSize(  size )
        self.SetMaxSize(  size )

        #bind events
        self._hover = False
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnToolLeave)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnToolEnter)

        self.longHelp = longHelp

    def AcceptsFocus(self):
        """ 
        Overloaded base class method
        """
        return False
        
    def SetShortHelp(self, shortHelp):
        """
        Set the short help string
        """
        self.SetToolTipString(shortHelp)

    def SetLongHelp(self, longHelp):
        """
        Set the long help string
        """
        self.longHelp = longHelp

    def SetToolWidth(self, w):
        """
        Call to set the tool width
        """
        size = self.GetSize()
        new = ( w, size[1] )
        self.SetSize( new )
        self.SetMinSize(  new )
        self.SetMaxSize(  new )

    def SetToolHeight(self, h):
        """
        Called by the ToolPanel when changing tool height
        """
        size = self.GetSize()
        new = ( size[0], h )
        self.SetSize( new )
        self.SetMinSize(  new )
        self.SetMaxSize(  new )

    def OnToolLeave(self, event):
        self._hover = False
        if self.Parent.statusbar is not None:
            self.Parent.statusbar.PopStatusText()
        event.Skip()

    def OnToolEnter(self, event):
        self._hover = True
        if self.Parent.statusbar is not None:
            #Do this as enter can be called before exit!
            wx.CallAfter(self.Parent.statusbar.PushStatusText, self.longHelp)
        event.Skip()


class TPStaticText(TPToolItem):
    """
    A static text control with the gradient background ToolPanel class
    """
    def __init__(self, parent, id, text):
        TPToolItem.__init__(self, parent, id)

        self.text = text
        w,h = self.GetTextExtent(self.text)
        self.SetToolWidth(w+4)
       
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)
        
    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        #draw background
        w, h = self.GetClientSizeTuple()        
        dc.SetPen(wx.Pen(self.Parent._bgcol))
        dc.SetBrush(wx.Brush(self.Parent._bgcol))
        dc.DrawRectangle(0, 0, w, h)

        #draw text
        dc.SetFont(self.GetFont());
        tw,th = self.GetTextExtent(self.text)
        x = (w-tw)/2
        y = (h-th)/2
        dc.DrawText(self.text, x, y);

    def OnSize(self, event):
        self.Refresh()
        event.Skip()


class TPSeperator(TPToolItem):
    """
    A seperator control with the gradient background ToolPanel class
    """
    def __init__(self, parent, id):
        TPToolItem.__init__(self, parent, id)
        self.SetToolWidth(8)
       
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)
        
    def OnPaint(self, event):

        dc = wx.PaintDC(self)
        #draw background
        w, h = self.GetClientSizeTuple()        
        dc.SetPen(wx.Pen(self.Parent._bgcol))
        dc.SetBrush(wx.Brush(self.Parent._bgcol))
        dc.DrawRectangle(0, 0, w, h)

        #draw lines
        x1 = (w/2)-1
        x2 = (w/2)
        y1 = 5
        y2 = h-6
        dc.SetPen(wx.Pen('#A2A2A2',width=1))
        dc.DrawLine( x1, y1, x1, y2)
        dc.SetPen(wx.Pen('#E3E3E3',width=1))
        dc.DrawLine( x2, y1, x2, y2)

    def OnSize(self, event):
        self.Refresh()
        event.Skip()


class TPButtonItem(TPToolItem):
    """
    A bitmap button tool item
    """
    def __init__(self,parent,id=-1,bmp=wx.NullBitmap):

        TPToolItem.__init__(self, parent, id)
        w = self.Parent.GetToolHeight()
        self.SetToolWidth(w)

        self.down = False  #button is down (pressed)

        self.bmp = bmp
        self.bmp_disabled = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()


        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE,             self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)

        self.Bind(wx.EVT_LEFT_DOWN,        self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP,          self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK,      self.OnLeftDown)
        self.Bind(wx.EVT_MOTION,           self.OnMotion)

        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

    def SetBitmap(self, bmp):
        """
        Set the bitmap
        """
        self.bmp = bmp
        self.bmp_disabled = bmp.ConvertToImage().ConvertToGreyscale().ConvertToBitmap()
        self.Refresh()
        
    #---events------------------------------------------------------------------
    def OnPaint(self, event):
        tic= time.time()
        dc = wx.PaintDC(self)
        
        #draw background
        w, h = self.GetClientSizeTuple()        
        dc.SetPen(wx.Pen(self.Parent._bgcol))
        dc.SetBrush(wx.Brush(self.Parent._bgcol))
        dc.DrawRectangle(0, 0, w, h)

        #draw bezel
        #hover = (wx.FindWindowAtPointer() is self)
        if self._hover is False and self.down is False:
            pass

        else:
            if self.IsEnabled() is False:
                state = wx.CONTROL_DISABLED
            elif self._hover and self.down is False:
                state = wx.CONTROL_CURRENT
            elif self._hover and self.down is True:
                state = wx.CONTROL_PRESSED
            elif self.down is True:
                state = wx.CONTROL_PRESSED
            #draw
            rect = wx.Rect(0, 0, w, h)
            wx.RendererNative.Get().DrawPushButton(self, dc, rect, state)

        #draw bitmap
        bmp = self.bmp
        if not self.IsEnabled():
            bmp = self.bmp_disabled
        bw,bh = bmp.GetWidth(), bmp.GetHeight()
        if self.down is True:
            dx = dy = 1
        else:
            dx = dy = 0
        hasMask = bmp.GetMask() != None
        dc.DrawBitmap(bmp, (w-bw)/2+dx, (h-bh)/2+dy, hasMask)

    def OnMouseEnter(self, event):
        self._hover=True
        self.Refresh()
        event.Skip()

    def OnMouseLeave(self, event):
        self._hover=False
        self.Refresh()
        event.Skip()

    def OnLeftDown(self, event):
        if not self.IsEnabled():
            return
        self.down = True
        self.CaptureMouse()
        self.Refresh()
        event.Skip()

    def OnLeftUp(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return
        if self.HasCapture():
            self.ReleaseMouse()
            if self.down is True:    # if the button was down when the mouse was released...
                #post an EVT_TOOL via the parent tool panel
                id  = event.GetId()
                evt = wx.CommandEvent( wx.wxEVT_COMMAND_TOOL_CLICKED, id)
                evt.SetEventObject(self)
                wx.PostEvent(self.Parent, evt)       
            self.down = False
            self.Refresh()

    def OnMotion(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return

        if event.LeftIsDown() and self.HasCapture():
            #check if hovering over this button
            x,y = event.GetPositionTuple()
            w,h = self.GetClientSizeTuple()
            if x<w and x>=0 and y<h and y>=0:
                #over button
                self.down = True
            else:
                #not over button
                self.down = False
            self.Refresh()
        event.Skip()

    def OnSize(self, event):
        self.Refresh()
        event.Skip()



class TPToggleItem(TPButtonItem):
    """
    A togglable bitmap button item.
    """
    def __init__(self,parent,id=-1,bmp=wx.NullBitmap):

        TPButtonItem.__init__(self, parent, id, bmp)
        w = self.Parent.GetToolHeight()
        self.SetToolWidth(w)

        self.state = False  #check/toggle state
    
    def SetToggle(self, flag):
        if isinstance(flag, bool) is False:
            raise ValueError('Expected a boolean')
        self.state = flag
        self.down = flag
        self.Refresh()

    def GetToggle(self):
        return self.state

    #---events------------------------------------------------------------------    
    def OnLeftDown(self, event):
        if not self.IsEnabled():
            return
        #(toggle state= not self.state)
        self.down = not self.state
        self.CaptureMouse()
        self.SetFocus()
        self.Refresh()

    def OnLeftUp(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return
        if self.HasCapture():
            self.ReleaseMouse()
            if self.down != self.state:
                #set state
                self.state = not self.state
                
                #post an EVT_TOOL via the parent tool panel
                id  = event.GetId()
                evt = wx.CommandEvent( wx.wxEVT_COMMAND_TOOL_CLICKED, id)
                evt.SetEventObject(self)
                evt.SetInt( int(self.state))
                wx.PostEvent(self.Parent, evt)  
            self.Refresh()

    def OnMotion(self, event):
        if not self.IsEnabled():
            return
        if event.LeftIsDown() and self.HasCapture():
            x,y = event.GetPositionTuple()
            w,h = self.GetClientSizeTuple()
            if x<w and x>=0 and y<h and y>=0:
                #over button flip state
                self.down = not self.state
                self.Refresh()
                return
            if (x<0 or y<0 or x>=w or y>=h):
                #not over button set back to state
                self.down = self.state
                self.Refresh()
                return
        event.Skip()

    def OnSize(self, event):
        self.Refresh()
        event.Skip()



class TPDropDown(TPToggleItem):
    """
    A bitmap button item with a drop down button for menus etc.
    """
    def __init__(self,parent,id=-1, bmp=wx.NullBitmap):

        TPToggleItem.__init__(self, parent, id, bmp)

        self.but_w = self.Parent.GetToolHeight()
        self.drp_w = 11
        self.SetToolWidth(self.but_w + self.drp_w)

    def PopupMenu(self, menu, pt=None):
        """Pop up a menu for the dropdown"""
        if pt is None:
            w,h = self.GetSize()
            pt = (0,h)
        wx.PyControl.PopupMenu(self, menu, pt)
        self.SetToggle(False)
        self._hover=False

    #---events------------------------------------------------------------------
    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        #draw background
        w, h = self.GetClientSizeTuple()        
        dc.SetPen(wx.Pen(self.Parent._bgcol))
        dc.SetBrush(wx.Brush(self.Parent._bgcol))
        dc.DrawRectangle(0, 0, w, h)

        #draw bezel
        if self._hover is False and self.down is False:
            pass
        else:
            if self.IsEnabled() is False:
                state = wx.CONTROL_DISABLED
            elif self._hover and self.down is False:
                state = wx.CONTROL_CURRENT
            elif self._hover and self.down is True:
                state = wx.CONTROL_PRESSED
            elif self.down is True:
                state = wx.CONTROL_PRESSED
            #draw
            rect = wx.Rect(0, 0, w, h)
            wx.RendererNative.Get().DrawPushButton(self, dc, rect, state)

        #draw bitmap
        bmp = self.bmp
        if not self.IsEnabled():
            bmp = self.bmp_disabled
        bw,bh = bmp.GetWidth(), bmp.GetHeight()
        if self.down is True:
            dx = dy = 1
        else:
            dx = dy = 0
        hasMask = bmp.GetMask() != None
        dc.DrawBitmap(bmp, (self.but_w-bw)/2+dx, (h-bh)/2+dy, hasMask)

        #if mouse over the control draw the dividing line
        x1 = self.but_w -2
        w = self.but_w -1 + self.drp_w
        if self._hover or self.down:
            #draw partial vertical line
            dc.SetPen(wx.Pen('#A2A2A2',width=1))
            dc.DrawLine( x1, 6, x1, h-6)

        #draw dropdown
        #Do dropdown
        #       #######     (height/2) -2
        #        #####          
        #         ###
        #          #
        #          (width/2) -1
        cenx = x1 + (self.drp_w/2)
        ceny = (h/2)
        dc.SetPen(wx.Pen('#000000',width=1))
        dc.DrawLine( cenx-3, ceny-1, cenx+3, ceny-1)
        dc.DrawLine( cenx-2, ceny,   cenx+2, ceny)
        dc.DrawLine( cenx-1, ceny+1, cenx+1, ceny+1)
        dc.DrawLine( cenx,   ceny+2, cenx, ceny+2)

    def OnLeftUp(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return
        if self.HasCapture():
            self.ReleaseMouse()
            if self.down != self.state:

                #Check if it is over the dropdown or button
                x,y = event.GetPositionTuple()
                w,h = self.GetSize()
                rect = wx.Rect( self.but_w, 0, self.drp_w, h)
                pt = self.ScreenToClient(wx.GetMousePosition())
                if rect.Contains(pt):
                    #set toggle state only if on dropdown
                    self.state = not self.state
                else:
                    self.down = not self.down

                #post an EVT_TOOL via the parent tool panel
                id  = event.GetId()
                evt = wx.CommandEvent( wx.wxEVT_COMMAND_TOOL_CLICKED, id)
                evt.SetEventObject(self)
                evt.SetInt( int(self.state))
                wx.PostEvent(self.Parent, evt)  

            self.Refresh()

#-------------------------------------------------------------------------------
def test():

    new_bmp     =  wx.ArtProvider.GetBitmap( wx.ART_NEW )
    open_bmp    =  wx.ArtProvider.GetBitmap( wx.ART_FILE_OPEN )
    save_bmp    =  wx.ArtProvider.GetBitmap( wx.ART_FILE_SAVE )
    f = wx.Frame(None, -1, 'test')
    sb = f.CreateStatusBar()

    sizer = wx.BoxSizer( wx.VERTICAL)

    tb =  ToolPanel( f, -1)
    tb.AddTool( wx.ID_NEW, new_bmp, wx.ITEM_NORMAL, 
                    'New file', 'Open a new file')

    tb.AddTool( wx.ID_OPEN, open_bmp, ITEM_DROPDOWN, 
                    'New file', 'Open a new file')
    tb.AddSeparator()
    tb.AddTool( wx.ID_SAVE, save_bmp, wx.ITEM_NORMAL, 
                    'New file', 'Open a new file')

    tb.AddSeparator()
    tb.AddStaticLabel( 'Test: ')

    id = tb.AddTool( -1, new_bmp, wx.ITEM_CHECK, 
                    'Toggle new', 'Toggle a new file')

    tb.AddTool( -1, new_bmp, wx.ITEM_NORMAL, 
                    'New file', 'Open a new file')

    tb.SetStatusBar(sb)
    sizer.Add( tb, 0, wx.EXPAND)
    f.SetSizer(sizer)

    f.Show()


    def handler(event):
        print 'In Handler', event.GetEventObject(), event.GetId(), event.Checked()
        
    def menu_handler(event):
        if event.Checked():
            #open menu
            menu = wx.Menu()
            
            for n in range(0,5):
                item = wx.MenuItem(menu, -1 ,'File'+str(n), '', wx.ITEM_NORMAL)
                menu.AppendItem(item)
            tool = event.GetEventObject()
            tool.PopupMenu(menu)
            menu.Destroy()
        else:
            print 'clicked'

    tb.Bind(wx.EVT_TOOL, handler, id=wx.ID_NEW)
    tb.Bind(wx.EVT_TOOL, menu_handler, id=wx.ID_OPEN)
    tb.Bind(wx.EVT_TOOL, handler, id=id)

    return f, tb

if __name__ == '__main__':
    app = wx.PySimpleApp() 
    f, tb = test()
    app.MainLoop()
