"""
A general purpose control for object addresses for use with tools such as 
Namespace browser and Inspector.

Features autocompletion of addresses fetched from the active engine.
Use the EVT_ENGINE_ADDRESS to get address changes
Automatically sends an EVT_ENGINE_ADDRESS when the engine state changes
to allow windows to refresh.

The engine name and address can be found from the event as event.engname and 
event.address. 
The address can be:
    ''   - top level namespace
or
    object name
or
    None if no engine is set as current
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

import wx
from wx.lib.newevent import NewEvent

from ptk_lib.engine import eng_messages
from ptk_lib.message_bus import mb_protocol
import console_messages

import autocomps

EvtEngineAddress , EVT_ENGINE_ADDRESS = NewEvent()

class AddressCtrl(wx.TextCtrl):
    def __init__(self,parent, id, msg_node, size=(200,-1)):
        """
        A text ctrl+autocomplete popup menu for entering object name addresses
        e.g. 'module.function'
        """ 
        wx.TextCtrl.__init__(self,parent,id, '',
                                size=size,style=wx.TE_PROCESS_ENTER)

        self.Bind( wx.EVT_TEXT_ENTER , self.OnTextEnter, self )

        #messagebus node to use
        self.msg_node = msg_node

        #get a reference to the console tool
        self.contool = wx.GetApp().toolmgr.get_tool('Console')

        #create popup window...
        self.dropdown =  AddressPopup(self)

        #attributes to keep track of address
        self._autoupdate = False #automatically update when engine state changes.
        self.cur_add = ''
        self.cur_eng = None

        #enginename: address dictionary for engine swicthing memory
        self.memory = {}
        self.msg_node.subscribe( console_messages.CONSOLE_SWITCHED, 
                                 self.msg_con_switched)
        self.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                self.msg_eng_disconnect)  
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_CHANGE, 
                                 self.msg_eng_change)
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_DONE, 
                                 self.msg_eng_change)

    def __del__(self):
        self.msg_node.unsubscribe( console_messages.CONSOLE_SWITCHED, 
                                 self.msg_con_switched)
        self.msg_node.unsubscribe( cmb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                self.msg_eng_disconnect)
        self.msg_node.unsubscribe( eng_messages.ENGINE_STATE_CHANGE, 
                                 self.msg_eng_change)
        self.msg_node.unsubscribe( eng_messages.ENGINE_STATE_DONE, 
                                 self.msg_eng_change)

    #---Interfaces--------------------------------------------------------------
    def SetEngine(self,engname):
        #store current address to memory
        self.memory[self.cur_eng] = self.cur_add
        if engname is not None:
            #check engine name
            if self.contool.get_engine_console(engname) is None:
                    raise NameError('Engine does not exist!')
                    
        #set engine and address
        self.cur_eng = engname
        if self.cur_eng is None:
            self.Disable()
        else:
            self.Enable()
        address= self.memory.get(engname,'')
        self.SetAddress(address)

    def GetEngine(self):
        """Get the current engine name this address control is using"""
        return self.cur_eng
        
    def SetAddress(self, address, engname=None):
        """
        Set the address. If engname is None this will set the address for the 
        current engine, otherwise it will set the address in the engine memory.
        """
        #print 'set address', address
        #get the current engine
        if engname is None:
            engname = self.cur_eng

        #check the address
        if engname is not None:
            exists = self._CheckAddress(engname, address)
            #if the address is invalid set the control back to the current
            if exists is False:
                #check cur address is ok
                if self._CheckAddress(engname, self.cur_add):
                    address = self.cur_add
                else:
                    #use top level.
                    address = ''

        #not the current engine store address if it exists and return.
        if engname!=self.cur_eng:
            self.memory[engname] = address
            return

        #set address in text control, store the new address as current
        self.dropdown.Hide()#hide autocomplete list
        self.dropdown.UpdateAutoComps(address)
        self.SetValue(address)
        self.cur_add = address

        #raise address event
        evt = EvtEngineAddress(engname=self.cur_eng, address=address)
        wx.PostEvent(self, evt)

    def GetAddress(self, engname=None):
        """
        Get the address. If engname is None this is for the current engine
        otherwise the address from the engine memory is returned.
        """
        if engname is None:
            engname = self.cur_eng

        if engname!=self.cur_eng:
            return self.memory.get(engname, '')

        return self.GetValue()
    
    def MoveUpLevel(self):
        """Change the address up one level"""
        address = self.GetValue()
        new = address.rpartition('.')[0]
        self.SetAddress(new)

    def RefreshAddress(self):
        """Refresh the current address"""
        self.SetAddress(self.cur_add)

    def SetAutoUpdate(self, flag=False):
        """
        Set whether an address event should be sent when the engine state 
        changes.
        """
        self._autoupdate = flag

    #---internal methods--------------------------------------------------------
    def _CheckAddress(self, engname, address):
        """
        Check an address. Returns True if ok, False if the address is invalid or
        the engine does not exist.
        """
        eng = self.contool.get_engine_console(engname)
        if eng is None:
            return False

        #check address
        if address!='':
            #not top level (top level is ok. but doesn't exist)
            return eng.run_task('object_exists',(address,))
        else:
            return True

    #---event handlers----------------------------------------------------------
    def OnTextEnter(self,event):
        #raise address event
        address = self.GetValue()
        self.SetAddress(address)

    #---message handlers--------------------------------------------------------
    def msg_con_switched(self,msg):
        """
        Message handler for console switched messages
        Load the previous address for the new engine (if it exists).
        """
        con = self.contool.get_current_engine()
        if con is not None:
            neweng = con.engine
        else:
            neweng = None
        self.SetEngine(neweng)

    def msg_eng_disconnect(self,msg):
        """
        Message handler for engine disconnected messages.
        Remove engine's address history.
        """
        engname = msg.get_data()[0]
        self.memory.pop(engname,None)
        
        #set to the new engine or None if no engines or not an engine console.
        con = self.contool.get_current_engine()
        if con is not None:
            neweng = con.engine
        else:
            neweng = None
        self.SetEngine(neweng)

    def msg_eng_change(self,msg):
        """
        Message handler for Engine.State.Done / Engine.State.Changed.
        Refresh the dropdown list
        """
        if self._autoupdate is False:
            return
        self.RefreshAddress()



#%%-----------------------------------------------------------------------------
# The custom popup control
#-------------------------------------------------------------------------------
class AddressPopup(wx.PopupWindow):
    def __init__(self, parent):
        """
        Custom address autocompletion popup window for address control
        """
        style = wx.BORDER_SIMPLE
        wx.PopupWindow.__init__(self, parent, style)

        #add a scrolledWindow to draw into
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ScrolledWindow(self, -1)  
        self.list.Bind( wx.EVT_PAINT, self.OnPaint)
        self.list.Bind( wx.EVT_SIZE, self.OnSize) 
        sizer.Add(self.list, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(sizer)
        
        #mouse clicks in the scrolled window
        self.list.Bind( wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.list.Bind( wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        
        #need to bind to parent to get keyboard/mouse events
        self.Parent.Bind( wx.EVT_TEXT , self.OnText )
        self.Parent.Bind( wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Parent.Bind( wx.EVT_CHAR, self.OnChar)
        self.Parent.Bind( wx.EVT_MOUSE_EVENTS, self.OnParentClick)
        self.Parent.Bind( wx.EVT_KILL_FOCUS, self.OnKillFocus )

        #internal data structures
        self.activeItem = -1    #active item
        self.items = []  #list of strings to display
        self.type = []  #list of type string
        
        self.objname = u''        #object namespace
        self.remainder=u''        #remainder word to search for
        self.SetBestItemSize()

    def UpdateAutoComps(self, value):
        """
        Get autocomps for the string value given.
        """
        #split the value into objname and remainder
        if value.count('.')==0:
            self.objname = ''
            self.remainder = value
        else:
            self.objname,self.remainder = value.rsplit('.',1)

        #use  get_auto_comps task to get possible names
        eng = self.Parent.contool.get_engine_console(self.Parent.cur_eng)
        if eng is not None:
            items = eng.run_task('get_autocomps_names',(self.objname,))
        else:
            items = []
            
        #sort these
        items.sort(lambda x, y: cmp(x[0].upper(), y[0].upper()))

        #add items
        self.items = items

        #set size
        self.SetBestItemSize()
        
        #set popup position
        self.SetBestPosition()

        #no items do nothing!
        if len(items)==0:
            self.activeItem = -1
        else:

            #search for remainder result
            found, n = self.Match(self.remainder)
            if found is True:
                self.activeItem = n
                self.list.Scroll(0, self.activeItem)
            else:
                self.list.Scroll(0, 0)

        
        #update the whole window
        if self.IsShown():
            self.Refresh(False)
    
    def SetBestItemSize(self):
        """
        Set the item size using system fonts.
        """
        #find the longest item string.
        text=''
        for n,t in self.items:
            if len(n)>len(text):
                text=n
        
        #calculate the best size width in system font should do...        
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        dc = wx.ClientDC(self)
        dc.SetFont(font)
        w, h = dc.GetTextExtent(text)
        if w<150: w=150
        self.itemw = w+32+32 #icon and scrollbars
        
        w, charh = dc.GetTextExtent('y')
        if charh<22: #22x22 px icon size
            self.itemh = 22
        else:
            self.itemh = charh
        self.texth = charh
            
        self.SetSize((self.itemw,self.itemh*8)) # 8 items/rows.
        self.list.SetScrollbars( self.itemw, self.itemh, 0, len(self.items))

        self.Layout()
        
    def SetBestPosition(self):
        """
        Set the best position for the popup
        """
        #get width of text control and position
        tw, th = self.Parent.GetSizeTuple()
        x, y = self.Parent.ClientToScreenXY(0,th)
        self.SetPosition( (x, y) )

    @property
    def nItems(self):
        return len(self.items)
    
    def SetActiveItem(self, n=0):
        """
        Set the active item number.
        n=-1 for no selection
        """
        nitems = len(self.items)
        if n<=-1:
            self.activeItem = -1
            self.list.Scroll(0, 0)
            self.Refresh()
            return
            
        if self.activeItem>0:
            self.activeItem=n
        if self.activeItem>(nitems-1):
            self.activeItem=nitems-1
        self.list.Scroll(0, self.activeItem)
        self.Refresh()

    def ItemUp(self, n=1):
        """
        Move the selected item up by n items
        """
        #none selected do nothing
        if self.activeItem == -1:
            return
            
        new =  self.activeItem - n
        nitems = len(self.items)
        if new<0:
            self.activeItem=0
        else:
            self.activeItem = new
            
        #scroll window
        curItem = self.list.GetViewStart()[1]
        if self.activeItem<curItem:
            self.list.Scroll(0, self.activeItem)
        self.Refresh()
        
    def ItemDown(self, n=1):
        """
        Move the selected item down by n items
        """
        #none selected do nothing
        if self.activeItem == -1:
            return
            
        new =  self.activeItem + n
        nitems = len(self.items)
        if new>(nitems-1):
            self.activeItem=nitems-1
        else:
            self.activeItem = new
        
        #scroll window
        curItem = self.list.GetViewStart()[1]
        if self.activeItem>= (curItem+7):
            self.list.Scroll(0, self.activeItem-7)
        self.Refresh()

    def Match(self, remainder):
        """
        Search for the item starting with string, remainder
        Returns, (found, n)
        """
        remainder = remainder.upper() #make upper for case insentitive search
        found = False
        n=0 #to avoid error when no items
        for n in range(0,len(self.items)):
            name,type = self.items[n]
            if name.upper().startswith(remainder):
                found = True
                break
        return found,n

    
    def Select(self):
        """
        Select the active item and hide the autocomp list
        """
        self.Hide()
        if self.activeItem<0:
            self.Cancel()
            
        name,t = self.items[self.activeItem]
        #print 'selected', name,t
        
        if len(self.objname)==0:
            new = name
        else:
            new = self.objname+'.'+name
        self.Parent.SetAddress(new)
        self.Parent.SetInsertionPoint(len(new))
        self.Hide()
        
    def Cancel(self):
        """
        Hide the autocomp list
        """
        #print 'cancelled'
        self.Hide()
        
    #events
    def OnPaint(self, evt):
        """
        Paint handler for scrolled window
        """
        dc = wx.PaintDC(self.list)
        dc.SetBackground( wx.WHITE_BRUSH)
        dc.Clear()
        
        self.list.PrepareDC(dc)
        vs  = self.list.GetViewStart()
        
        # determine the subset of the items that need to be drawn
        w,h = self.list.GetClientSize()
        itemStart = vs[1]
        itemStop  = vs[1] + h/self.itemh +1
        if itemStart <0:
            itemStart = 0
        if itemStop > len(self.items):
            itemStop = len(self.items)
        #print itemStart, itemStop
        
        #calculate yoffset for text/icon
        dy_text = (self.itemh-self.texth)/2
        if dy_text <0:
            dy_text=0
        x_text = 32 
        dy_icon = (self.itemh-22)/2
        if dy_icon <0:
            dy_icon=0
        x_icon = 5
        
        #setup colours to use
        c1 = wx.WHITE
        c2 = wx.BLACK
        c1h = wx.SystemSettings.GetColour(wx.wx.SYS_COLOUR_MENUHILIGHT)
        c2h = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        dc.SetPen(wx.Pen(c1))
        dc.SetBrush(wx.Brush(c1))
        dc.SetTextBackground(c1)
        dc.SetTextForeground(c2)
        
        #fetch the standard icons
        app = wx.GetApp()
        nsb = app.toolmgr.get_tool('NSBrowser')

        none_icon = nsb.get_type_icon(-1) #default object name, type=type_string
        #loop over items to draw
        for n in range(itemStart, itemStop, 1):
            text,type = self.items[n]
            y = self.itemh*n
            
            if n==self.activeItem:
                #set active colours
                dc.SetPen(wx.Pen(c1h))
                dc.SetBrush(wx.Brush(c1h))
                dc.SetTextBackground(c1h)
                dc.SetTextForeground(c2h)
                
                #draw active higlight
                dc.DrawRectangle(0,y,self.itemw,self.itemh)
                dc.DrawText( text, x_text, y+dy_text)

                #restore colours
                dc.SetTextBackground(c1)
                dc.SetTextForeground(c2)
                
            else:
                dc.DrawText(text, x_text, y+dy_text)
                
            #draw icon
            #get from nsb/type tool
            icon = nsb.get_type_icon(type)
            if icon is None:
                icon = none_icon
            dc.DrawIcon( icon, x_icon, y+dy_icon)
            
    def OnSize(self, event):
        #update the whole window
        self.Refresh(False)
 
    def OnLeftDown(self, event):
        """mouse click event handler for popup"""
        win = wx.FindWindowAtPointer()
        if win not in (self, self.list):
            self.Hide()
            return
        n = self.list.GetScrollPos(wx.VERTICAL) + (event.GetY()/self.itemh) 
        self.activeItem = n
        self.Refresh()

    def OnLeftDClick(self, event):
        n = self.list.GetScrollPos(wx.VERTICAL) + (event.GetY()/self.itemh) 
        self.activeItem = n
        self.Refresh()
        self.Select()

    #parent TextCtrl events
    def OnText(self,event):
        value=self.Parent.GetValue()
        self.UpdateAutoComps(value)
        event.Skip()
 
    def OnKeyDown(self, event):
        """Key down event handler of (parent textctrl)."""
        #get key info
        key         = event.GetKeyCode() #always capital letters here
        #controlDown = event.CmdDown()    #use CmdDown to support mac command button and win/linux ctrl
        #altDown     = event.AltDown()
        #shiftDown   = event.ShiftDown()
        
        #if the autocomp popup is not shown pass the events to the parent
        if self.IsShown() is False:
            event.Skip()
            return
        
        #enter/cancel
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER,wx.WXK_RIGHT, wx.WXK_TAB]:
            self.Select()
        elif key in [wx.WXK_ESCAPE, wx.WXK_LEFT]:
            self.Cancel()

        #move active items
        elif key==wx.WXK_UP:
            self.ItemUp()
        elif key==wx.WXK_DOWN:
            self.ItemDown()
        elif key==wx.WXK_PAGEUP:
            self.ItemUp(8)
        elif key==wx.WXK_PAGEDOWN:
            self.ItemDown(8)
        elif key==wx.WXK_HOME:
            self.SetActiveItem(0)
        elif key==wx.WXK_END:
            self.SetActiveItem(self.nItems)  
        #backspace
        elif key==wx.WXK_BACK: 
            #no remainder word left - cancel/hide list
            if len(self.remainder)<=1:
                self.Cancel()
                event.Skip()
                return
                
            #adjust remainder of word
            self.remainder = self.remainder[:-1]
            
            #search for new match
            found, n = self.Match(self.remainder)
            if found is True:
                self.activeItem = n
                self.list.Scroll(0, self.activeItem-1)
                self.Refresh()
            else:
                #no selection
                self.activeItem = -1
                self.list.Scroll(0, 0)
                self.Refresh()
                
            event.Skip() #allow stc to delete the last character
            
        #Everything else pass to stc
        else:
            event.Skip()
        
    def OnChar(self, event):
        """Char event handler (parent stc) called after OnkeyDown"""
        char = unichr(event.GetUnicodeKey())
        #print 'On Char',char, self.remainder+char, self.mode
        
        #if the autocomp popup is not shown pass the events to the parent
        if self.IsShown() is False:
            self.Show()
            
        #special check for name autocompletes - update autocomps when '.'
        if char == '.':
            #get the current value from text ctrl and update
            value = self.Parent.GetValue()
            self.UpdateAutoComps( value+char)
        else:
            #update the remainder string and search for matches
            self.remainder = self.remainder + char
            #search for remainder result
            found, n = self.Match(self.remainder)
            if found is True:
                self.activeItem = n
                self.list.Scroll(0, self.activeItem-1)
            else:
                #not found no active item
                self.activeItem = -1
                self.list.Scroll(0, 0)

        self.Refresh()
        event.Skip() #skip to allow stc to update

    def OnParentClick(self, event):
        """Capture clicks in parent text ctrl"""
        #if hidden pass to parent
        if self.IsShown() is False:
            event.Skip()
            return
            
        #otherwise check for clicks
        if event.ButtonDown():
            self.Cancel()
            event.Skip()

    def OnKillFocus(self, event):
        self.Hide()
        event.Skip()

#%%-----------------------------------------------------------------------------
# Simple address control for mac os platform without popup support.
#-------------------------------------------------------------------------------
class SimpleAddressCtrl(wx.TextCtrl):
    """Mac OS doesn't supportpopups! use this simple control instead"""
    def __init__(self,parent, id, msg_node, size=(200,-1)):
        wx.TextCtrl.__init__(self,parent,id, '',
                                size=size,style=wx.TE_PROCESS_ENTER)
        self.Bind( wx.EVT_TEXT_ENTER , self.OnTextEnter, self )

        #messagebus node to use
        self.msg_node = msg_node

        #get a reference to the engine manager tool
        self.contool = wx.GetApp().toolmgr.get_tool('Console')

        #attributes to keep track of address
        self._autoupdate = False #automatically update when engine state changes.
        self.cur_add = ''
        self.cur_eng = None

        #enginename: address dictionary for engine swicthing memory
        self.memory = {}
        self.msg_node.subscribe( console_messages.CONSOLE_SWITCHED, 
                                 self.msg_con_switched)
        self.msg_node.subscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                self.msg_eng_disconnect)  
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_CHANGE,
                                 self.msg_eng_change)
        self.msg_node.subscribe( eng_messages.ENGINE_STATE_DONE, 
                                 self.msg_eng_change)

    def __del__(self):
        self.msg_node.unsubscribe( console_messages.CONSOLE_SWITCHED, 
                                 self.msg_con_switched)
        self.msg_node.unsubscribe( mb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                self.msg_eng_disconnect)
        self.msg_node.unsubscribe( eng_messages.ENGINE_STATE_CHANGE, 
                                 self.msg_eng_change)
        self.msg_node.unsubscribe( eng_messages.ENGINE_STATE_DONE, 
                                 self.msg_eng_change)

    #---Interfaces--------------------------------------------------------------
    def SetEngine(self,engname):

        #store current address to memory
        self.memory[self.cur_eng] = self.cur_add
        if engname is not None:
            #check engine name
            if self.contool.get_engine_console(engname) is None:
                    raise NameError('Engine does not exist!')
                    
        #set engine and address
        self.cur_eng = engname
        if self.cur_eng is None:
            self.Disable()
        else:
            self.Enable()
        address= self.memory.get(engname,'')
        self.SetAddress(address)

    def GetEngine(self):
        """Get the current engine name this address control is using"""
        return self.cur_eng
        
    def SetAddress(self,address,engname=None):
        """
        Set the address. If engname is None this will set the address for the 
        current engine, otherwise it will set the address in the engine memory.
        """
        #get the current engine
        if engname is None:
            engname = self.cur_eng

        #check the address
        if engname is not None:
            exists = self._CheckAddress(engname, address)
            #if the address is invalid set the control back to the current
            if exists is False:
                #check cur address is ok
                if self._CheckAddress(engname, self.cur_add):
                    address = self.cur_add
                else:
                    #use top level.
                    address = ''

        #not the current engine store address if it exists and return.
        if engname!=self.cur_eng:
            self.memory[engname] = address
            return

        #set address in text control, store the new address as current
        self.SetValue(address)
        self.cur_add = address

        #raise address event
        evt = EvtEngineAddress(engname=self.cur_eng, address=address)
        wx.PostEvent(self, evt)

    def GetAddress(self, engname=None):
        """
        Get the address. If engname is None this is for the current engine
        otherwise the address from the engine memory is returned.
        """
        if engname is None:
            engname = self.cur_eng

        if engname!=self.cur_eng:
            return self.memory.get(engname, '')

        return self.GetValue()
    
    def MoveUpLevel(self):
        """Change the address up one level"""
        address = self.GetValue()
        new = address.rpartition('.')[0]
        self.SetAddress(new)

    def RefreshAddress(self):
        """Refresh the current address"""
        self.SetAddress(self.cur_add)

    def SetAutoUpdate(self, flag=False):
        """
        Set whether an address event should be sent when the engine state 
        changes.
        """
        self._autoupdate = flag

    #---internal methods--------------------------------------------------------
    def _CheckAddress(self, engname, address):
        """
        Check an address. Returns True if ok, False if the address is invalid or
        the engine does not exist.
        """
        eng = self.contool.get_engine_console(engname)
        if eng is None:
            return False

        #check address
        if address!='':
            #not top level (top level is ok. but doesn't exist)
            return eng.run_task('object_exists',(address,))
        else:
            return True

    #---event handlers----------------------------------------------------------
    def OnTextEnter(self,event):
        #raise address event
        address = self.GetValue()
        self.SetAddress(address)

    #---message handlers--------------------------------------------------------
    def msg_con_switched(self,msg):
        """
        Message handler for console switched.
        Load the previous address for the new engine (if it exists).
        """
        con = self.contool.get_current_engine()
        if con is not None:
            neweng = con.engine
        else:
            neweng = None
        self.SetEngine(neweng)

    def msg_eng_disconnect(self,msg):
        """
        Message handler for Engine.Disconnect.
        Remove engine's address history.
        """
        engname = msg.get_data()[0]
        self.memory.pop(engname,None)
        #set to the new engine or None if no engines or not an engine console.
        con = self.contool.get_current_engine()
        if con is not None:
            neweng = con.engine
        else:
            neweng = None
        self.SetEngine(neweng)

    def msg_eng_change(self,msg):
        """
        Message handler for Engine.State.Done / Engine.State.Changed.
        Refresh the dropdown list
        """
        if self._autoupdate is False:
            return
        self.RefreshAddress()


#use simple address ctrl on mac
if wx.Platform == '__WXMAC__':
    AddressCtrl = SimpleAddressCtrl

#-------------------------------------------------------------------------------
def test():
    f= wx.Frame(None,-1,'Test')
    s = wx.BoxSizer(wx.VERTICAL)
    a = AddressCtrl(f,-1)
    s.Add(a, 0, wx.ALL,5)
    f.SetSizer(s)
    f.Show()
    return f
