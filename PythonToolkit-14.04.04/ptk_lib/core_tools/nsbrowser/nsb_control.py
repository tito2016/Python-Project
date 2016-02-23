"""
Namespace browser control 

NSBrowserControl - Panel class with toolbar and lsit
NSBrowserList - Virtual list control class
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import wx
from ptk_lib.resources import common16
from ptk_lib.controls import AddressedMenu, AutoSizeListCtrl
from ptk_lib.controls import toolpanel

from ptk_lib.core_tools.console import AddressCtrl, EVT_ENGINE_ADDRESS

import nsb_icons #icons
import nsb_tasks


#---The main panel--------------------------------------------------------------
class NSBrowserControl(wx.Panel):
    def __init__(self, parent, tool):
        wx.Panel.__init__(self, parent, id=-1)
        
        #get reference to tools/message node
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')
        self.tool = tool
        self.msg_node = tool.msg_node

        #create controls
        self._CreateTools()
        self.list = NSBrowserList(self,tool)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.tools, 0, wx.EXPAND,0 )
        vbox.Add(self.list, 1, wx.EXPAND,0)
        self.SetSizer(vbox)         

    def _CreateTools(self):
        """Creates the toolbar panel in the browser"""

        self.tools = toolpanel.ToolPanel(self,-1)
        self.tools.SetStatusBar(self.console.frame.StatusBar)
        #set the icon size
        self.tools.SetToolBitmapSize((16,16))

        #load some icons
        save_bmp    = common16.document_save.GetBitmap()
        open_bmp    = common16.document_open.GetBitmap()
        refresh_bmp = common16.view_refresh.GetBitmap()
        clear_bmp   = common16.edit_delete.GetBitmap()
        up_bmp      = common16.go_up.GetBitmap()
        filter_bmp  = nsb_icons.filter_choice.GetBitmap()

        #export
        self.export_id = wx.NewId()
        self.tools.AddTool( self.export_id, save_bmp, wx.ITEM_NORMAL,
                            shortHelp='Export objects',
                            longHelp='Open the Export dialog')
        self.Bind(wx.EVT_TOOL, self.OnExport, id=self.export_id)
        
        #import
        self.import_id = wx.NewId()
        self.tools.AddTool(self.import_id, open_bmp, wx.ITEM_NORMAL,
                            shortHelp='Import data',
                            longHelp='Import saved data')
        self.Bind(wx.EVT_TOOL, self.OnImport, id=self.import_id)
        self.tools.AddSeparator()

        #clear
        self.clear_id = wx.NewId()
        self.tools.AddTool(self.clear_id , clear_bmp, wx.ITEM_NORMAL,
                            shortHelp='Clear the main namespace',
                            longHelp='Clears the main namespace')
        self.Bind(wx.EVT_TOOL, self.OnClear ,id=self.clear_id )
        self.tools.AddSeparator()

        #Current namespace
        self.tools.AddStaticLabel('Current namespace: ')
        self.addbar = AddressCtrl(self.tools,-1,self.msg_node, size=(150, -1))
        self.addbar.SetAutoUpdate(True)
        self.tools.AddControl(self.addbar)
        self.addbar.Bind(EVT_ENGINE_ADDRESS, self.OnAddress)

        #refresh
        self.refresh_id = wx.NewId()
        self.tools.AddTool(self.refresh_id, refresh_bmp, wx.ITEM_NORMAL,
                            shortHelp='Refresh the namespace listing',
                            longHelp='Refresh the namespace listing')
        self.Bind(wx.EVT_TOOL, self.OnRefresh ,id=self.refresh_id)
        
        #up a level
        self.up_id = wx.NewId()
        self.tools.AddTool(self.up_id,up_bmp, wx.ITEM_NORMAL,
                            shortHelp='Move up a namespace level',
                            longHelp='Move up a namespace level')
        self.Bind(wx.EVT_TOOL, self.OnUp ,id=self.up_id)

        #filter selection dropdown menu
        self.filter_id = wx.NewId()
        self.tools.AddTool(self.filter_id, filter_bmp, toolpanel.ITEM_DROPDOWN,
                            shortHelp='Select filters',
                            longHelp='Select the filters to apply')

        self.Bind(wx.EVT_TOOL, self.OnFilter ,id=self.filter_id)

    def _CreateFilterMenu(self):
        #filter selection dropdown menu
        #Show modules
        fmenu = wx.Menu()

        #show types
        item = wx.MenuItem(fmenu, wx.NewId(),"Show types/classes",kind=wx.ITEM_CHECK)
        fmenu.AppendItem(item)
        if self.list.show_types is True: item.Toggle()
        self.Bind(wx.EVT_MENU, self.OnShowTypes, item)

        #show instances
        item = wx.MenuItem(fmenu, wx.NewId(),"Show instances",kind=wx.ITEM_CHECK)
        fmenu.AppendItem(item)
        if self.list.show_inst is True: item.Toggle()
        self.Bind(wx.EVT_MENU, self.OnShowInst, item)

        #show functions/methods
        item = wx.MenuItem(fmenu, wx.NewId(),"Show routines",kind=wx.ITEM_CHECK)
        fmenu.AppendItem(item)
        if self.list.show_call is True: item.Toggle()
        self.Bind(wx.EVT_MENU, self.OnShowRoutines, item)

        item = wx.MenuItem(fmenu, wx.NewId(),"Show modules",kind=wx.ITEM_CHECK)
        fmenu.AppendItem(item)
        if self.list.show_mod is True: item.Toggle()
        self.Bind(wx.EVT_MENU, self.OnShowMods, item)

        #show hidden
        item = wx.MenuItem(fmenu, wx.NewId(),"Show hidden objects",kind=wx.ITEM_CHECK)
        fmenu.AppendItem(item)
        if self.list.show_hidden is True: item.Toggle()
        self.Bind(wx.EVT_MENU, self.OnShowHidden, item)

        return fmenu

    #---Interface methods-------------------------------------------------------
    #address
    def GetAddress(self, engname=None):
        """Get the current namespace address (if engname is given the address from 
        the memory is returned)"""
        return self.addbar.GetAddress(engname)

    def SetAddress(self,newadd,engname=None):
        """Set the current namespace address (if engname is given the address in 
        the memory is set)"""
        self.addbar.SetAddress(newadd,engname)

    def RefreshAddress(self):
        """Update the list control to show the current dir listing"""
        self.addbar.RefreshAddress()

    #clear/rename/copy/delete
    def ClearMain(self):
        """Clear the main namespace"""
        eng = self.console.get_current_engine()
        if eng is None:
            return

        msg = "Clear the main namespace (deletes all references)?\n(Note: this does not unload any modules)"
        dlg = wx.MessageDialog(self, msg, "Clear main namespace",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:

            try:
                ok = eng.run_task('clear_main')
            except NameError:
                eng.register_task(nsb_tasks.clear_main)
                ok = eng.run_task('clear_main')

            self.SetAddress('')
            #publish engine state change message
            eng.notify_change()
        dlg.Destroy()

    
    def Rename(self,onames):
        """Rename the objects given in the list onames."""
        eng = self.console.get_current_engine()
        if eng is None:
            return
        for oname in onames:
            dlg = wx.TextEntryDialog(None, 'Rename '+oname+' to:','Rename:', '')
            if dlg.ShowModal() == wx.ID_OK:
                new = dlg.GetValue()
                if new != oname:
                    try:
                        ok = eng.run_task('rename_object',(oname,new)) 
                    except:
                        eng.register_task(nsb_tasks.rename_object)
                        ok = eng.run_task('rename_object',(oname,new)) 

                    #publish engine state change message
                    eng.notify_change()           
            dlg.Destroy()

    def Copy(self,onames):
        """Copy the objects given in the list onames."""
        eng = self.console.get_current_engine()
        if eng is None:
            return
        for oname in onames:
            dlg = wx.TextEntryDialog(None, 'Copy '+oname+' as:','Copy:', '')
            if dlg.ShowModal() == wx.ID_OK:
                new = dlg.GetValue()
                try:
                    ok = eng.run_task('copy_object',(oname,new))
                except NameError:
                    eng.register_task(nsb_tasks.copy_object)
                    ok = eng.run_task('copy_object',(oname,new))

            dlg.Destroy()
        #publish engine state change message
        eng.notify_change()

    def Delete(self,onames):
        """Delete the objects given in the list onames."""
        eng = self.console.get_current_engine()
        if eng is None:
            return
        if len(onames)==1:
            msg = "Delete object "+onames[0]+"?"
        else:
            msg = "Delete selected objects?"
        dlg = wx.MessageDialog(None, msg, "Delete",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            for oname in onames:
                eng.execute('del('+oname+')')
            #publish engine state change message
            eng.notify_change()
        dlg.Destroy()

    def Export(self, onames):
        self.msg_node.send_msg('FileIO','Export',(self.addbar.GetEngine(),onames))

    def Import(self):
        self.msg_node.send_msg('FileIO','Import',())

    #---Toolbar events----------------------------------------------------------
    def OnExport(self,event):
        #get the selected items from the list
        onames, type_strings = self.list.GetSelectedObjectInfo()
        self.Export(onames)

    def OnImport(self,event):
        self.Import()

    def OnClear(self,event):
        """Clears the main namespace"""
        self.ClearMain()

    def OnRefresh(self,event):
        """Refresh the dir listings of the current namespace"""
        self.RefreshAddress()

    def OnFilter(self,event):
        """Open the filters popup menu"""
        tool = event.GetEventObject()
        
        if tool.GetToggle() is False:
            tool.SetToggle( True )
            tool.Refresh()
        
        #open the menu
        fmenu = self._CreateFilterMenu()
        
        tool.PopupMenu(fmenu)
        fmenu.Destroy()

    def OnAddress(self,event):
        """Address bar modified"""
        self.list.PopulateList(event.engname,event.address)
        if event.engname == None:
            enable = False
        else:
            enable =True
        self.Enable(enable)    #enable/disable list
        self.tools.EnableTool(self.export_id , enable)
        self.tools.EnableTool(self.import_id , enable)
        self.tools.EnableTool(self.clear_id , enable)
        self.tools.EnableTool(self.refresh_id , enable)
        self.tools.EnableTool(self.up_id , enable)
        self.tools.EnableTool(self.filter_id , enable)

    def OnUp(self,event):
        """Move up a level"""
        self.addbar.MoveUpLevel()

    #---filter events-----------------------------------------------------------    
    def OnShowTypes(self,event):
        """Show types/classes filter"""
        self.list.show_types = event.IsChecked() 
        self.list.FilterList() 

    def OnShowInst(self,event):
        """Show instances filter"""
        self.list.show_inst = event.IsChecked() 
        self.list.FilterList()

    def OnShowRoutines(self,event):
        """Show Routiness filter"""
        self.list.show_call = event.IsChecked() 
        self.list.FilterList()
    
    def OnShowMods(self,event):
        """Show modules filter"""
        self.list.show_mod = event.IsChecked() 
        self.list.FilterList()

    def OnShowHidden(self,event):
        """Show hidden items filter"""
        self.list.show_hidden = event.IsChecked() 
        self.list.FilterList()
    

#---List control----------------------------------------------------------------
class NSBrowserList(AutoSizeListCtrl):
    def __init__(self,parent, tool):
        #create the list control
        AutoSizeListCtrl.__init__(self,parent, wx.ID_ANY, style=wx.BORDER_SUNKEN
                |wx.LC_VIRTUAL|wx.LC_REPORT| wx.LC_VRULES| wx.LC_HRULES )

        #get a reference to the tools needed
        self.tool = tool #the NSBrowser tool instance
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #dict of type_string: flags exceptions (i.e. numpy.ufunc does not 
        #register as a routine
        self.flag_overides = {}

        #filter settings
        self.show_types = True
        self.show_inst = True
        self.show_call = True
        self.show_mod = True
        self.show_hidden = False

        #internals
        self.cur_add =''       #namespace address
        self.cur_eng = None
        self.dirlist=[]         #curent dir listing (name,type,istype,isinst,isfunc,ismod)
        self.items = []         #list of items (name,type) to show

        self.sort_current = 0       #current sort method (0=name,1=type)
        self.sort_namedir = False   #direction of sort on object name (reverse=)
        self.sort_typedir = False   #direction of sort on object type (reverse=)  

        #set up image list
        self.ilist = wx.ImageList(22,22)
        self.idict = {} #dict of {otype:index}
        self.SetImageList(self.ilist,wx.IMAGE_LIST_SMALL)
        #add default icon
        icon = self.tool.get_type_icon(-1)
        self.idict[-1] = self.ilist.AddIcon(icon)

        #set up fonts
        font = self.GetFont()
        font.SetPointSize(8)
        self.SetFont(font)

        #add columns
        self.InsertColumn(0, 'Object', width=130)
        self.InsertColumn(1, 'Type', width=130)
        self.InsertColumn(2, 'Info/Value', width=200)

        #event bindings
        #for column sorting see column sort mixin this is the event that is used
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLDClick)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick)
        self.Bind(wx.EVT_LIST_KEY_DOWN, self.OnKeyDown)

    #---interface methods-------------------------------------------------------
    def PopulateList(self, engname, address):
        """
        Update the list control for the given address.
        """
        #get the engine interface
        if engname is None:
            eng = None
        else:
            eng = self.console.get_engine_console(engname)
        self.cur_eng = engname

        #check that an engine interface was returned
        if eng is None:
            self.dirlist = []
            self.cur_add = ''
        else:
            #returns list of (name,type_string,istype,isrout,ismod,isinst)
            try:
                self.dirlist = eng.run_task('get_dir_list',(address,)) 
            except NameError:
                eng.register_task(nsb_tasks.get_dir_list)
                self.dirlist = eng.run_task('get_dir_list',(address,)) 

            self.cur_add = address
        self.FilterList()

    def FilterList(self):
        #clear the current list
        self.DeleteAllItems()
        #loop over the list and get the items to display
        self.items = []
        for item in self.dirlist:
            oname,type_string,istype,isrout, ismod, isinst = item
            #check overrides
            if self.flag_overides.has_key(type_string):
                istype,isrout,ismod,isinst = self.flag_overides[type_string]

            #check if we should add this item to the list
            ok = True
            if istype==True and self.show_types!=True:
                ok = False
            if isinst==True and self.show_inst!=True:
                ok = False
            if isrout==True and self.show_call!=True:
                ok = False
            if ismod==True and self.show_mod!=True: 
                ok = False

            #special check for hidden objects
            if oname.startswith('_')==True and self.show_hidden!=True:
               ok = False

            #if ok to show add the item to the items list
            if ok is True:
                self.items.append(item)

        self.SetItemCount(len(self.items))

        #sort the list
        if self.sort_current ==0:
            self.SortByName()
        else:
            self.SortByName()
            self.SortByType()

    def SortByName(self):
        """Sort the items by name"""
        #sort by name
        self.items.sort(reverse=self.sort_namedir)
        self.Refresh()

    def SortByType(self):
        """Sort items by type"""
        #sort by type
        templist = [ (line[1], line) for line in self.items ]
        templist.sort(reverse=self.sort_typedir)
        self.items = [ line[1] for line in templist ]
        self.Refresh()

    def DeSelectAll(self):
        """Deselect all the selected items"""
        n = self.GetSelectedItemCount()
        i = 0
        for n in xrange(0,n):
            i = self.GetNextSelected(i)
            self.Select(i,False)

    def SetFilterOverride(self,type_string, flags):
        """
        Set the flags to use for objects of the type given - this allows 
        numpy.ufunc to appear as routines.
        flags = (istype,isrout,ismod,isinst) filter flags
        """
        self.flag_overides[type_string] = flags

    def GetSelectedObjectInfo(self):
        """
        Get a selected object info, return a list of object names and object types
        """
        onames=[]
        otypes=[]
        n=self.GetFirstSelected()
        while n!=-1:
            oname,type_string,istype,isrout,ismod,isinst = self.items[n]
            #get full object name
            if self.cur_add!='':
                name = self.cur_add+'.'+oname
            else:
                name = oname   
            onames.append(name)
            otypes.append(type_string)
            n=self.GetNextSelected(n)
        return onames,otypes

    #---virtual list control functions------------------------------------------
    def OnGetItemText(self, row, col):
        if row>len(self.items)-1:
            return None
        eng = self.console.get_engine_console(self.cur_eng) 

        #catch no open engine case
        if eng is None:
            return None

        #get row
        oname,type_string,istype,isrout,ismod,isinst = self.items[row]

        #need the name
        if col==0:
            return oname
        #need the type (last bit of type_string only)
        elif col==1:
            return type_string #.rpartition('.')[-1]
        #need the info/value
        elif col==2:
            #get the full object name
            if self.cur_add!='':
                name = self.cur_add+'.'+oname
            else:
                name = oname
            #get the info/value string
            info = self.tool.get_type_info(type_string)
            if info is None:
                info = self.tool.get_type_info(-1)
            try:
                infostr = info(eng, name)
            except:
                infostr = 'UNKNOWN'

            #check value
            if infostr is None:
                infostr = 'UNKNOWN'
            return infostr
        #another column!?!
        else:
            return None

    def OnGetItemImage(self, row):
        """Get the icon number to use for the item in row=row)"""
        if row>len(self.items)-1:
            return None

        oname,type_string,istype,isrout,ismod,isinst = self.items[row]

        #check if the icon has already been used in the list
        if self.idict.has_key(type_string):
            n = self.idict[type_string]
        else:
            #not used previously get it
            icon = self.tool.get_type_icon(type_string)
            if icon is None:
                n=self.idict[-1]
            else:
                n = self.ilist.AddIcon(icon)
                self.idict[type_string] = n
        return n

    def OnGetItemAttr(self, row):
        return None

    #---List events-------------------------------------------------------------
    def OnLDClick(self,event):
        """When an item is double clicked perform the object types defualt action"""
        n=self.GetFocusedItem()
        nselected = self.GetSelectedItemCount()

        #make sure an item was clicked not blank space!
        if n==-1 or nselected==0:
            return

        oname,type_string,istype,isrout,ismod,isinst = self.items[n]
        
        #get the full object name
        if self.cur_add!='':
            name = self.cur_add+'.'+oname
        else:
            name = oname

        #check if there is a viewer for this item
        try:
            viewtool = wx.GetApp().toolmgr.get_tool('Views')
            hasview = viewtool.has_type_view(type_string)
        except:
            hasview=False

        if hasview is False:
            #none defined so browse to this object.
            self.Parent.addbar.SetAddress(name)
        else:
            #use the view for this type.
            viewtool.open_viewer_pane(self.cur_eng,name)

    #---context menus-----------------------------------------------------------
    def OnContextMenu(self,event):
        """event method for open context menu"""
        onames, type_strings = self.GetSelectedObjectInfo()
        if len(onames)==1:
            cmenu = self.CreateContextMenu(onames[0],type_strings[0])
        elif len(onames)>1:
            cmenu = self.CreateContextMenuMultiple(onames,type_strings)
        else:
            return
        
        #display the menu
        self.PopupMenu(cmenu)
        cmenu.Destroy()

    def CreateContextMenu(self,oname,type_string):
        """Create a context menu based upon the selected object"""
        cmenu = AddressedMenu()

        #add the 'Open' command only if a view is defined
        try:
            viewtool = wx.GetApp().toolmgr.get_tool('Views')
            has_view = viewtool.has_type_view(type_string)
        except:
            has_view = False
        if has_view is True:
            item = cmenu.AppendItem( wx.NewId(),'Open',help='Open a view of the object')
            cmenu.Bind(wx.EVT_MENU, self.OnOpenView, item)
            cmenu.AppendSeparator('')

        #add the standard actions, Rename,Copy,Delete and Export
        item = cmenu.AppendItem( wx.NewId(),'Rename',help='Rename the object')
        do = lambda event, a=self.Parent.Rename: a([oname])
        cmenu.Bind(wx.EVT_MENU, do, item)

        item = cmenu.AppendItem( wx.NewId(),'Copy',help='Copy the object')
        do = lambda event, a=self.Parent.Copy: a([oname])
        cmenu.Bind(wx.EVT_MENU, do, item)

        item = cmenu.AppendItem( wx.NewId(),'Delete',help='Delete the object')
        do = lambda event, a=self.Parent.Delete: a([oname])
        cmenu.Bind(wx.EVT_MENU, do, item)

        item = cmenu.AppendItem( wx.NewId(),'Export',help='Export the object')
        do = lambda event, a=self.Parent.Export: a([oname])
        cmenu.Bind(wx.EVT_MENU, do, item)

        #add the actions
        cmenu.AppendSeparator(address='')
        actions = self.tool.get_type_actions([type_string])
        actions = zip(actions.keys(),actions.values()) #sort the addresses
        actions.sort()
        for address,action in actions:
            item = cmenu.AppendItem( wx.NewId(),address,help=action.helptip)
            do = lambda event, a=action: a(self.cur_eng,[oname])
            cmenu.Bind(wx.EVT_MENU, do, item)
        #return the constructed menu
        return cmenu

    def CreateContextMenuMultiple(self,onames,type_strings):
        """Create a context menu for mutliple selected objects"""
        cmenu = AddressedMenu()
        #add the standard actions, Rename,Copy,Delete

        item = cmenu.AppendItem( wx.NewId(),'Rename objects',help='Rename the objects')
        do = lambda event, a=self.Parent.Rename: a(onames)
        cmenu.Bind(wx.EVT_MENU, do, item)

        item = cmenu.AppendItem( wx.NewId(),'Copy objects',help='Copy the objects')
        do = lambda event, a=self.Parent.Copy: a(onames)
        cmenu.Bind(wx.EVT_MENU, do, item)

        item = cmenu.AppendItem( wx.NewId(),'Delete objects',help='Delete the objects')
        do = lambda event, a=self.Parent.Delete: a(onames)
        cmenu.Bind(wx.EVT_MENU, do, item)
        
        item = cmenu.AppendItem( wx.NewId(),'Export',help='Export the objects')
        do = lambda event, a=self.Parent.Export: a(onames)
        cmenu.Bind(wx.EVT_MENU, do, item)

        #Add allowed actions
        cmenu.AppendSeparator(address='')
        actions = self.tool.get_type_actions(type_strings)
        actions = zip(actions.keys(),actions.values()) #sort the addresses
        actions.sort()
        for address,action in actions:
            item = cmenu.AppendItem( wx.NewId(),address,help=action.helptip)
            do = lambda event, a=action: a(self.cur_eng,onames)
            cmenu.Bind(wx.EVT_MENU, do, item)
        #return the constructed menu
        return cmenu

    def OnColClick(self,event):
        """Column click event handler"""
        col=event.GetColumn()
        if col==0:
            #sort by name
            self.sort_namedir = not self.sort_namedir
            self.sort_current = 0
            self.SortByName()
        elif col==1:
            #sort by type
            self.sort_typedir = not self.sort_typedir
            self.sort_current = 1
            self.SortByType()

    def OnKeyDown(self,event):
        """Key ddown event handler"""
        kc = event.GetKeyCode()
        #TODO: search on linux - works automatically on windows
        #print kc,chr(kc)
        event.Skip()

    #---context menu events-----------------------------------------------------
    def OnOpenView(self,event):
        """Open a view for the selected object"""
        n=self.GetFocusedItem()
        oname,type_string,istype,isrout,ismod,isinst = self.items[n]
        
        #get the full object name
        if self.cur_add!='':
            name = self.cur_add+'.'+oname
        else:
            name = oname
        #use the view for this type.
        viewtool = wx.GetApp().toolmgr.get_tool('Views')
        viewtool.open_viewer_pane(self.cur_eng,name)
