"""
Console autocompletion popup, engine tasks and logic.
"""
import os
import wx
import wx.stc as stc #for test function
from wx.lib.embeddedimage import PyEmbeddedImage

from console_icons import autocomp_arg,autocomp_key, autocomp_folder, autocomp_file, autocomp_dbg
#%%-----------------------------------------------------------------------------
#Algorithm:
#-------------------------------------------------------------------------------
BRK_SEPS = ('[','(',')',']', '{','}')
WHT_SEPS = (' ','\t')
ETC_SEPS = ('\n', ',', ';', ':' ,
        '+', '-', '/', '*', '%',
        '&', '|', '^', '~',
        '=', '<', '>' )
ALL_SEPS = BRK_SEPS+ETC_SEPS+WHT_SEPS
  
  
    
def number_check(string):
    """
    Check if a string evals to a number safely - tests for decimal, hex (0x), 
    binary (0b) and oct (0o) number formats
    """
    #check it's not a number
    try:
        float(string)
        #is a number return
        return True
    except:
        #carry on
        pass
    
    #check for hex
    if string.startswith(('0x', '0X')):
        try:
            float.fromhex(string)
            return True
        except:
            #carry on
            pass
        
    #check for binary
    if string.startswith(('0b','0B')):
        try:
            int(string, 2)
            return True
        except:
            pass
    
    #check for Oct
    if string.startswith(('0o','0O')):
        try:
            int(string, 8)
            return True
        except:
            pass
        
    return False
    
def scan_line(line):
    """
    Scan the line and determine if in a string, a call or an indexing bracket. 
    Return the object and remainder string needed for autocompletes.

    Notes:
    - only the most recent bracket is valid) e.g. object.callable( dict[ key 
    would be in_index but not in_call
    - the end string returned will not include calls/indexing that needs to be 
    evaluated. i.e. 
    object().name returns remainder=.name
    object[index].name returns remainder=.name

    Returns in_str, in_call, in_index, objname, remainder
    """
    #1) Scan the line of code for seperator strings ignoring seperators that 
    #occur within strings. Generate a list of (sep,pos) tuples to interesting 
    #seperators in the line.
    str_found = False
    found = []
    n = 0 
    while n < len(line):

        #check for string opening
        if line[n:n+3] in ('"""',"'''"):
            sep = line[n:n+3]
            str_found = True
        elif line[n] in ('"',"'"):
            sep = line[n]
            str_found = True

        #a string open/close
        if str_found:
            found.append( (sep, n) )

            #find close
            pos2 = line.find(sep, n+len(sep))
            if pos2==-1:
                #no close found
                n = len(line) #move to end
            else:
                #found close move on
                found.append( (sep, pos2))
                n = pos2+len(sep)
            str_found = False #reset flag

        #another seperator at this position
        elif line[n] in ALL_SEPS:
            found.append( (line[n], n))
            n=n+1
        else:
            n=n+1

    #2)Determine if in a string, call or index
    in_str  = False
    in_call = False
    in_index = False

    #-------------------
    #no seperators case
    #-------------------
    if len(found)==0:
        remainder = line
        #no further checking necessary return
        return in_str, in_call, in_index, "", remainder

    #---------------------
    # Check if in a string
    #---------------------
    #find the last remainder - end string
    sep,pos = found[-1]
    remainder = line[pos+len(sep):]
    if sep in ("'''",'"""','"',"'"):
        in_str = True
        remainder = sep+remainder

    #-----------------------
    # Check if in call/index
    #-----------------------
    #find position of last unclosed bracket
    ss, ps = zip(*found) #split into seps/pos
    n = len(found)-1     #scan backwards to get last callable
                         #i.e.  t = (callable1(callable2( arg
    while n>-1:
        s,p = found[n]
        #check for an unbalanced (
        if (s=='(') and ((ss[n:].count('(') - ss[n:].count(')'))>0):
            #check the character before to determine if a valid call or
            #just a bracket/tuple
            if p>0 and line[p-1] not in ETC_SEPS+BRK_SEPS:
                in_call = True
                break

        #check for an unbalanced [
        if (s=='[') and ((ss[n:].count('[') - ss[n:].count(']'))>0):
            #check the character before to determine if a valid index or
            #just a list
            if p>0 and line[p-1] not in ETC_SEPS+BRK_SEPS:
                in_index = True
                break

        #reduce n to continue search
        n-=1

    #not in call/index no more work needed return
    if (not in_call) and (not in_index):
        return in_str, in_call, in_index, "", remainder

    #Find the start of the name before the bracket
    if n==0:
        p2 = 0
    else:
        s2,p2 = found[n-1]
        #discard any seperators than are white space only.
        while s2 in WHT_SEPS:
            n-=1
            if n==0:
                p2 = 0
                break
            s2,p2 = found[n-1]
            p2=p2+1 #adjust to get correct portion of string
        
    #strip any remaining white space
    objname = line[p2:p].strip(''.join(WHT_SEPS))
        
    return in_str, in_call, in_index, objname, remainder


#%%-----------------------------------------------------------------------------
# Engine tasks
#-------------------------------------------------------------------------------
#Autocomp_names:
def get_autocomps_names(globals, locals, objname):
    """
    Engine task to get autocomplete names for the objname given.
    """
    import __builtin__
        
    #No address, a top level object
    if objname =='':
        #get the names from the locals and globals
        names = locals.keys()       
        for name in globals.keys():
            #only add global name if not already in the locals
            if name not in names:
                names.append(name)

        #get the builtins
        try:
            builtinlist = eval("__builtins__.dir(__builtins__)",globals, locals)
            for name in builtinlist:
                if name not in names:
                    names.append(name)
        except:
            pass

    #Need to get object then dir listing 
    else:
        #if address contains a call or index DO NOT EVALUATE!
        if objname.count(')') >0:
            names = []
        elif objname.count(']') >0:    
            names = []
        else:
            try:
                obj = eval(objname, globals, locals)
                names = __builtin__.dir( obj )
            except:
                names = []      

    #get type strings and build full address and make item = (name,type) tuple
    items = []
    for name in names:
        try:
            #get the object
            if objname not in ['',u'']:
                oname = objname+'.'+name
            else:
                oname = name
            obj = eval(oname, globals, locals)

            #get type_string
            t = type(obj)
            type_string = t.__module__ + '.' + t.__name__
        except:
            type_string = 'UNKNOWN'
            
        items.append( (name, type_string) )

    return items

#Autocomp keys:
def get_autocomps_keys(globals, locals, objname, quote):
    """
    Engine task to get autocomplete keys from the dict given by objname.
    """
    import __builtin__
    import collections

    #if address contains a call or index DO NOT EVALUATE! could be blocking
    if objname.count(')') >0:
        return []
    if objname.count(']') >0:    
        return []

    #get the object
    try:
        obj = eval(objname, globals, locals)
    except:
        return []

    #check if actually dict-like
    if isinstance(obj,collections.Mapping) is False:
        dictlike = False
    #fails for some dictlike objects (shelve.Shelve)
    if hasattr(obj, 'keys'):
        dictlike = True
    if not dictlike:
        return []

    #only want string/unicode keys
    items = []
    for k in obj.keys():
        if isinstance(k, basestring):
            items.append( (quote+k+quote,0) )
            
    return items

#Autocomp kwargs:
def get_autocomps_args(globals, locals, objname):
    """
    Engine task to get autocomplete arguments from the callable with the address
    given. 

    Returns items
    """
    import inspect
    
    #if address contains a call or index DO NOT EVALUATE!
    if objname.count(')') >0:
        return []
    if objname.count(']') >0:    
        return []

    try:
        obj = eval(objname, globals, locals)
        argspec = inspect.getargspec(obj)
    except:
        return []

    names = argspec.args
    types = [1,]*len(names) 
    items = zip(names,types)
    return items

#autocomp path:
def get_autocomps_path(globals, locals, path_str):
    """
    Engine task to get possible file path autocompletes.
    path_str is the string/path to search for.

    Returns items, quote and os.sep
    """
    import os.path
  
    #strip the starting quote - if included.
    if path_str.startswith( ('"""',"'''") ):
        quote = path_str[0:3]
    elif path_str.startswith( ('"',"'") ):
        quote = path_str[0]
    else:
        quote = ''

    path_str = path_str[len(quote):]

    #split into base/file remainders
    dirname,basename = os.path.split(path_str)
    
    #get all possible names in this directory   
    try:
        names = os.listdir(dirname)
    except:
        names = []
        
    items = []
    for n in names:
        if dirname=='/':
            path = dirname+n
        elif dirname.endswith('\\'):
            path = dirname+n
        else:
            path = dirname+os.sep+n
        #fix windows paths
        path = path.replace('\\', '\\'*2)
        path = path.replace('\\'*4, '\\'*2)
        if os.path.isfile(path):
            t = 2
        elif os.path.isdir(path):
            t = 3
        else:
            #neither assume a file!
            t = 2
        items.append( (quote+path+quote, t) )
        
    #now look in current working directory if required
    cwd = os.getcwdu()
    if cwd == dirname or dirname!='':
        return items, quote, os.sep
    
    if os.path.isdir(cwd+os.sep+dirname):
        names = os.listdir(cwd+os.sep+dirname)
        
    for n in names:
        if dirname in ('','/'):
            path = n
        elif dirname.endswith('\\'):
            path = n
        else:
            path = dirname+os.sep+n
        #fix windows paths
        path = path.replace('\\', '\\'*2)
        path = path.replace('\\'*4, '\\'*2)
        if os.path.isfile(path):
            t = 2
        elif os.path.isdir(path):
            t = 3
        else:
            #neither assume a file!
            t = 2
        items.append( (quote+path+quote, t))

    return items, quote, os.sep



#%%-----------------------------------------------------------------------------
# The custom popup control - allows more control than default STC
# implementation.
#-------------------------------------------------------------------------------
class AutoComp(wx.PopupWindow):
    def __init__(self, parent, pos=wx.DefaultPosition):
        """
        Custom autocompletion popup window for console stc.
        """
        style = wx.BORDER_SIMPLE
        wx.PopupWindow.__init__(self, parent, style)
        self.SetPosition(pos)

        #add a scrolledWindow to draw into
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ScrolledWindow(self, -1)  
        self.list.Bind(wx.EVT_PAINT, self.OnPaint)
        self.list.Bind(wx.EVT_SIZE, self.OnSize) 
        sizer.Add(self.list, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(sizer)
        
        #need to bind to parent to get keyboard events
        #parent must have keyboard focus!
        self.Parent.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Parent.Bind(wx.EVT_CHAR, self.OnChar)
        
        self.list.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        self.Parent.Bind(wx.EVT_MOUSE_EVENTS, self.OnParentClick)

        #internal data structures
        self.activeItem = -1    #active item
        self.items = []  #list of strings to display
        self.type = []  #list of type string
        self.remainder=u''        #remainder word to search for

        self.sep = '/'       #for path completions store the engine os.sep
        self.quote='"'       #and oepn string quotations


        app = wx.GetApp()
        self.nsb = app.toolmgr.get_tool('NSBrowser')
        
        self.SetBestItemSize()

    def ShowAutoComps(self, line):
        """
        Get autocomps for the line given.
        """
        # Modes are:
        # 0 = keys only
        # 1 = paths only
        # 2 = names only
        # 3 = args + names (top level namespace only)
        # 4 = keys + names (top level namespace only)

        
        ##determine mode
        instr, incall, inindex, objname, remainder = scan_line(line)
        #print instr,incall,inindex,';',objname,';', remainder

        #check if in a string cases first
        if instr and inindex:
            #a string inside an index
            #get string keys for object only (mode=0)
            self.mode = 0
           
        elif instr:
            #a string anywhere else get possible filepath completions (mode=1)
            self.mode = 1
        
        #next check if the remainder string contains a '.' as even if in a call or
        #index the autocomps should show only names, e.g. callable( name.s
        #should show names for the 'name' object
        elif remainder.count('.')!=0:
            # . in remainder string get names only (mode=2)
            self.mode = 2

        #next check for calls and indexing
        elif incall:
            #in a call get kwargs for callable objname also get object names for 
            #remainder e.g. "objname( end" (mode=3)
            #todo: what to do when line ends:
            # 'kwarg=xxx' or 'kwarg=' and remainder='xxx' or ''
            self.mode = 3
            
        elif inindex:
            #if in a index get any string keys (like instr case above, but not 
            #already in a string. e.g. objname[ remainder (mode = 4)
            self.mode = 4
            
        else:
            #only get the object names not handled above i.e toplevel only
            self.mode = 2
                
        #print self.mode

        ##Get autocomps
        #get string keys for object only (mode=0)
        if self.mode==0:
            if len(remainder)>0:
                if remainder.startswith(("'''",'"""')):
                    quote = remainder[0:3]
                else:
                    quote = remainder[0]
            else:
                quote = '"'
            items = self.Parent.run_task('get_autocomps_keys', (objname,quote))
        
        #paths only
        elif self.mode==1:
            items, quote, sep = self.Parent.run_task('get_autocomps_path',(remainder,) )
            self.quote = quote
            self.sep = sep

        #names only
        elif self.mode==2:
            #check if string is a number
            if number_check(remainder) is True:
                items = []
            else:
                parts = remainder.rsplit('.',1)
                if len(parts)>1:
                    name_obj,remainder = parts
                else:
                    name_obj= ''
                    remainder = parts[0]
                    #get items
                items = self.Parent.run_task('get_autocomps_names', (name_obj,))

        #names and args
        elif self.mode==3:
            items = self.Parent.run_task('get_autocomps_args', (objname,))
            #top level names only
            #check if string is a number
            if number_check(remainder) is True:
                pass
            else:
                items = items + self.Parent.run_task('get_autocomps_names', ('',))
            
        #names and string keys
        elif self.mode==4:
            if len(remainder)>0:
                if remainder.startswith(("'''",'"""')):
                    quote = remainder[0:3]
                else:
                    quote = remainder[0]
            else:
                quote = '"'
            items = self.Parent.run_task('get_autocomps_keys', (objname,quote))
            #top level names only
            #check if string is a number
            if number_check(remainder) is True:
                pass
            else:
                items = items + self.Parent.run_task('get_autocomps_names', ('',))

        #get debugger commands
        if (self.Parent.debugging is True):
            #name, type=4 (debugger command)
            ditems = [
            ('#help (or #h) - Show help text', 4),
            ('#step (or #s) - Step to next line', 4),
            ('#stepin (or #si) step in', 4),
            ('#stepout (or #so) to step out', 4),
            ('#resume (or #r) to resume', 4 ),
            ('#setscope (or #ss) set active scope',4),
            ('#line (or #l) print the current line', 4),
            ('#end (or #e) disable debugging and resume', 4) ]

            if line.startswith('#'):
                #only show debugger commands
                items = ditems
            else:
                items = items+ditems

        #print 'Found:',len(items),'items'
        #no items do nothing!
        if len(items)==0:
            return

        #add items
        self.SetItems( items, remainder)
        
        #set popup position
        self.SetBestPosition()
        
        #and show
        self.Show()
        
    #item methods
    def SetItems(self, items, remainder=u''):
        """
        Set the autocomplete items
        """
        
        #sort these and return
        items.sort(lambda x, y: cmp(x[0].upper(), y[0].upper()))
        
        self.items = items
        self.SetBestItemSize()

        #search for remainder result
        self.remainder = unicode(remainder)


        #search for remainder result
        found, n = self.Match(self.remainder)
        if found is True:
            self.activeItem = n
            self.list.Scroll(0, self.activeItem-1)
            self.Refresh()
        else:
            #not found no active item
            self.activeItem = -1
            self.list.Scroll(0, 0)
            self.Refresh()

        #update the whole window
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
        
        #hard coded min sizes
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
        #calculate where to show the calltip
        wpos = self.Parent.PointFromPosition(self.Parent.GetCurrentPos())
        spos = self.Parent.ClientToScreen(wpos)
        
        #size popup and parent stc
        size = self.GetSize()
        psize = self.Parent.GetSize()
        
        #screen size
        maxy = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_Y)
        maxx = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_X)
        
        spos.x = spos.x+50 #shift over a bit
        if spos.x > maxx:
            spos.x = maxx-size.x
            spos.y = spos.y-size.y-50
        if spos.y>maxy-size.y:
            spos.y = maxy-size.y
        if spos.y<0:
            spos.y = 0
            
        self.SetPosition(spos)

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
        name,t = self.items[self.activeItem]
        #print 'selected', name,t

        #check item is selected
        if (self.activeItem!=-1):
            name,t = self.items[self.activeItem]
            if t==0:
                #key - add ]
                name = name+']'
            if t==1:
                #arg - add =
                name = name+'='
            if t==4:
                #debugger command - strip comment
                name = name.split(' (')[0]

        else:
            name = self.remainder

        curpos  = self.Parent.GetCurrentPos()
        self.Parent.SetSelection(curpos-len(self.remainder), curpos)
        self.Parent.ReplaceSelection(name)

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
        key_icon = autocomp_key.GetIcon()        #key autocomps type=0
        arg_icon = autocomp_arg.GetIcon()        #args autocomps type=1
        file_icon = autocomp_file.GetIcon()      #filepath autocomps type=2
        folder_icon = autocomp_folder.GetIcon()  #folder path autocomp type=3
        debug_icon = autocomp_dbg.GetIcon()        #key autocomps type=4
        none_icon = self.nsb.get_type_icon(-1)   #default object name, type=type_string
        #loop over items to draw
        for n in range(itemStart, itemStop, 1):
            text,type = self.items[n]
            
            #if a path display only the base name
            if type in (2,3):

                #strip the starting/trailing quote
                l = len(self.quote)
                text = text[l:-l]

                #strip the starting/trailing quote
                #if text.startswith( ('"""',"'''") ):
                #    quote = text[0:3]
                #else:
                #    quote = text[0]
                #l = len(quote)
                #text = text[l:-l]

                #try to split using the last os.sep retreived from the engine
                parts = text.rsplit(self.sep,1)
                if len(parts)==1:
                    text = parts[0]
                else:
                    text = parts[1]

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
            if type==0:
                icon = key_icon
            elif type==1:
                icon = arg_icon
            elif type==2:
                icon = file_icon
            elif type==3:
                icon = folder_icon
            elif type==4:
                icon = debug_icon
            else:
                #get from nsb/type tool
                icon = self.nsb.get_type_icon(type)
                if icon is None:
                    icon = none_icon
            dc.DrawIcon( icon, x_icon, y+dy_icon)
            
    def OnSize(self, event):
        #update the whole window
        self.Refresh(False)
 
    def OnKeyDown(self, event):
        """Key down event handler of (parent stc)."""
        #get key info
        key         = event.GetKeyCode() #always capital letters here
        controlDown = event.CmdDown()    #use CmdDown to support mac command button and win/linux ctrl
        #altDown     = event.AltDown()
        #shiftDown   = event.ShiftDown()
        
        #if the autocomp popup is not shown pass the events to the parent
        if self.IsShown() is False:
            event.Skip()
            return
        
        #enter/cancel
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            self.Select()
        elif key in [wx.WXK_ESCAPE, wx.WXK_LEFT]:
            self.Cancel()
        elif key in  [wx.WXK_RIGHT, wx.WXK_TAB]:
            #if path autocomps tab/right arrow pressed on a folder item update 
            #the autocomp list 
            if (self.mode == 1) and (self.activeItem!=-1):
                name,t = self.items[self.activeItem]
                if (t == 3):
                    #add text to stc (including last os.sep retreived from engine)
                    if self.sep == '\\':
                        sep = '\\'*2
                    else:
                        sep = self.sep
                    curpos  = self.Parent.GetCurrentPos()
                    self.Parent.SetSelection(curpos-len(self.remainder), curpos)
                    self.Parent.ReplaceSelection(name[:-len(self.quote)]+sep)

                    #update items
                    line = self.Parent.GetCommand()
                    self.ShowAutoComps(line)
                else:
                    self.Select()
            else:
                self.Select()

        #move active items
        elif key==wx.WXK_UP:
            if controlDown:
                #search in command history
                self.Cancel()
                event.Skip()
            else:
                self.ItemUp()
                
        elif key==wx.WXK_DOWN:
            if controlDown:
                #search in command history
                self.Cancel()
                event.Skip()
            else:
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
                
            #special case for path - refresh when a os.sep is removed
            if self.mode == 1:
                char = self.remainder[-1]          
                if char==self.sep:
                    #get the current line of input from console stc
                    line = self.Parent.GetCommand()
                    self.ShowAutoComps( line[:-1])
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
        #if the autocomp popup is not shown pass the events to the parent
        if self.IsShown() is False:
            event.Skip()
            return
        char = unichr(event.GetUnicodeKey())
        #print 'On Char',char, self.remainder+char, self.mode

        #check for chars that should close the autocomps
        if len(self.remainder)>0:
            first = self.remainder[0]
        else:
            first = None

        if self.mode==0:
            # 0 = keys only
            #close on end quote:
            if char==first:
                self.Hide()
                event.Skip()
                return
                
        elif self.mode==1:
            # 1 = paths only
            #close on end quote
            if (self.remainder+char).endswith(self.quote):
                self.Hide()
                event.Skip()
                return
                
        elif self.mode in (2,3,4):
            # 2 = names only
            # 3 = args + names (top level namespace only)
            # 4 = keys + names (top level namespace only)
            # end on seperator character only if not in a quote.
            if first in ['"',"'"]:
                #close on end quote:
                if (self.remainder+char).endswith(self.quote):
                    self.Hide()
                    event.Skip()
                    return
            else:
                if char in ALL_SEPS:
                    self.Hide()
                    event.Skip()
                    return

        #if remainder is '' and the user starts a quote update autocomps
        #to ensure only keys are displayed and not names.
        if (self.mode==4)  and (first is None) and (char in ['"', "'"]):
            #get the current line of input from console stc
             line = self.Parent.GetCommand()
             self.ShowAutoComps(line+char)
             event.Skip()
             return
        
        #special check for path autocompletes - update autocomps when '/' or'\'
        if (self.mode == 1) and (char == self.sep):
            #get the current line of input from console stc
            line = self.Parent.GetCommand()
            self.ShowAutoComps( line+char)
            event.Skip()
            return
            
        #special check for name autocompletes - update autocomps when '.'
        elif (self.mode in (2,3,4)) and (char == '.'):
            #get the current line of input from console stc
            line = self.Parent.GetCommand()
            self.ShowAutoComps( line+char)
            event.Skip()
            return

        #update the remainder string and search for matches
        self.remainder = self.remainder + char
        #search for remainder result
        found, n = self.Match(self.remainder)
        if found is True:
            self.activeItem = n
            self.list.Scroll(0, self.activeItem-1)
            self.Refresh()
        else:
            #not found no active item
            self.activeItem = -1
            self.list.Scroll(0, 0)
            self.Refresh()
        event.Skip() #skip to allow stc to update

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

    def OnParentClick(self, event):
        """Capture clicks in parent stc"""

        #if hidden pass to parent
        if self.IsShown() is False:
            event.Skip()
            return
        #otherwise check for clicks
        if event.ButtonDown():
            self.Cancel()



