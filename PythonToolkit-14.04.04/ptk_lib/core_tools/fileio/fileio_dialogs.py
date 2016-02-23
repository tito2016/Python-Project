"""
Various export related dialogs:

Export dialog - The main exporter dialog window - select an exporter and the 
objects to export.

MultipleObjectToFileDialog - A dialog to use when multiple objects need to be 
exported each to a seperate file supporting automatic file naming.

MultipleObjectToFilePanel - The panel handling file naming for inclusion in a
custom dialog.
"""
import os
import os.path
import time
import wx
from ptk_lib.message_bus import mb_protocol
from ptk_lib.engine import eng_messages

from ptk_lib.controls import AutoSizeListCtrl, EditListCtrl, ScrolledText
from ptk_lib.controls.iconbutton import CollapsablePanel

#---Standard open dialog function-----------------------------------------------
def DoFileDialog(parent,message="Choose a file",
                defaultFile="",
                wildcard='All files|*.*;*',
                style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR,
                engname = None):
    """
    Create and display a file open box returns list of filepaths and the index
    of the filter selected by the user
    """
    #Get the current working directory
    console = wx.GetApp().toolmgr.get_tool('Console')
    if engname is None:
        eng = console.get_current_engine()
    else:
        eng = console.get_engine_console(engname)

    if eng is None:
        cwd = os.getcwd()
    else:
        cwd = eng.run_task('get_cwd')

    #Create the file open dialog.
    dlg = wx.FileDialog(
        parent, message=message,
        defaultDir=cwd, 
        defaultFile=defaultFile,
        wildcard = wildcard,
        style=style )

    #get file paths
    if dlg.ShowModal() == wx.ID_OK:
        # This returns a Python list of files that were selected.
        paths = dlg.GetPaths()
    else:
        paths = None

    #get type index.
    index = dlg.GetFilterIndex()

    dlg.Destroy()# Destroy the dialog.

    return paths, index

#---Export dialog---------------------------------------------------------------
class ExportDialog(wx.Dialog):
    def __init__(self, engname, onames):
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')
        parent = self.console.frame
        
        wx.Dialog.__init__(self, parent,-1,title='Export objects',
                            style=wx.DEFAULT_DIALOG_STYLE| wx.RESIZE_BORDER,
                            size=(720,420))
        #internal attributes
        self.engname = None
        self.names = {} #dict of objects to export {oname:typestring}
        self.exporter = None #current exporter
        self.types = [-1]

        #get references to required core tools.
        self.console = app.toolmgr.get_tool('Console')
        self.fileio = app.toolmgr.get_tool('FileIO')
        self.nsbtool = app.toolmgr.get_tool('NSBrowser')

        #create controls
        self._InitControls()

        #set up an image list to use for type icons
        self.il =  wx.ImageList(22, 22)
        self.idict = {} #typestring:icon index
        icon = self.nsbtool.get_type_icon(-1)        #add default icon
        self.idict[-1] = self.il.AddIcon(icon)
        self.tree.SetImageList(self.il)
        self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        #setup tree / names list
        self.SetEngine(engname)
        for name in onames:
            self.AddName(name)

        #subscribe to messages
        self.fileio.msg_node.subscribe( mb_protocol.SYS_NODE_DISCONNECT+'.Engine',
                                        self.msg_eng_change)
        self.fileio.msg_node.subscribe(eng_messages.ENGINE_STATE_CHANGE,
                                        self.msg_eng_change)
        self.fileio.msg_node.subscribe(eng_messages.ENGINE_STATE_DONE, 
                                        self.msg_eng_change)

    def _InitControls(self):
        #viszer to hold all controls
        vsizer = wx.BoxSizer(wx.VERTICAL)

        #exporter selection box
        box = wx.StaticBox(self, -1, "Select Exporter:")
        boldfont = box.GetFont()
        boldfont.SetWeight(wx.BOLD)
        box.SetFont(boldfont)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        vsizer.Add(bsizer,0,wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,10)

        #exporter selection list
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self,-1,"Export using:", size=(175,-1))
        hsizer.Add(label,0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        #setup list of exporters
        self.exporters = self.fileio.get_exporters()
        if len(self.exporters)==0:
            self.exporter = None
            self.types = [-1]
        else:
            self.exporter = self.exporters[0]
            self.types = self.exporter.type_strings
        names = []
        for exp in self.exporters:
            names.append(exp.name)

        self.exlist = wx.Choice(self, -1, choices=names, size=(300,-1))
        self.exlist.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnExporterChoice, self.exlist)
        hsizer.Add(self.exlist,0,wx.EXPAND|wx.ALL,5)
        bsizer.Add(hsizer, 0, wx.EXPAND,0)

        #export description
        if self.exporter is None:
            descrip = 'Select an exporter above.'
        else:
            descrip = self.exporter.get_description()
        self.descrip = ScrolledText(self, -1, descrip, size=(-1,40))
        bsizer.Add(self.descrip, 0, wx.EXPAND|wx.ALL,5)

        #object selection box
        box = wx.StaticBox(self, -1, "Select objects to export:")
        box.SetFont(boldfont)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        vsizer.AddSpacer((-1,5))
        vsizer.Add(bsizer,1,wx.EXPAND|wx.LEFT|wx.RIGHT,10)

        #engine selection list
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self,-1,"Export from Engine:", size=(175,-1))
        hsizer.Add(label,0,wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.engnames = self.console.get_engine_names()
        englabels = self.console.get_engine_labels()
        self.englist = wx.Choice(self, -1, choices=englabels, size=(300,-1))
        self.Bind(wx.EVT_CHOICE, self.OnEngineChoice, self.englist)
        hsizer.Add(self.englist,0,wx.EXPAND|wx.ALL,5)
        bsizer.Add(hsizer, 0, wx.EXPAND,0)

        #object selections bit
        splitter = wx.SplitterWindow(self,-1, style = wx.SP_LIVE_UPDATE)
        bsizer.Add(splitter, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        #tree
        self.tree = wx.TreeCtrl(splitter, -1, style=wx.TR_LINES_AT_ROOT|
                                wx.BORDER_SUNKEN|wx.TR_HAS_BUTTONS|
                                wx.TR_HIDE_ROOT| wx.TR_FULL_ROW_HIGHLIGHT|
                                wx.TR_MULTIPLE)
        panel = wx.Panel(splitter, -1)
        psizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding)
        self.root = self.tree.AddRoot('', 0, 0, data=wx.TreeItemData(('','')))

        butsizer = wx.BoxSizer(wx.VERTICAL)
        add_but  = wx.Button(panel, wx.ID_ANY, "Add")
        rem_but  = wx.Button(panel, wx.ID_ANY, "Remove")
        clr_but  = wx.Button(panel, wx.ID_ANY, "Remove All")
        butsizer.Add( add_but, 0, wx.ALL,0)
        butsizer.Add( rem_but, 0, wx.ALL,0)
        butsizer.Add( clr_but, 0, wx.ALL,0)
        psizer.Add(butsizer,0,wx.EXPAND|wx.ALL,5)
        self.Bind(wx.EVT_BUTTON, self.OnAdd, add_but)
        self.Bind(wx.EVT_BUTTON, self.OnRemove, rem_but)
        self.Bind(wx.EVT_BUTTON, self.OnClear, clr_but)

        self.list = AutoSizeListCtrl(panel, -1, 
                                style=wx.LC_REPORT 
                                 | wx.BORDER_SUNKEN
                                 | wx.LC_HRULES)
        self.list.InsertColumn(0, 'Object Name', width=130)
        self.list.InsertColumn(1, 'Type', width=130)

        psizer.Add(self.list, 1, wx.EXPAND)
        panel.SetSizer(psizer)
        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.tree, panel, 250)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        vsizer.Add(line,0,wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT,5)
        next_but    = wx.Button(self, wx.ID_OK, "Next")
        cancel_but= wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( cancel_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        butsizer.Add( next_but, 0, wx.ALIGN_RIGHT|wx.ALL,5)
        vsizer.Add(butsizer,0, wx.ALIGN_RIGHT)

        self.Bind(wx.EVT_BUTTON, self.OnNext, next_but)

        self.SetSizer(vsizer)        

    def __del__(self):
        #unsubscribe from messages
        self.fileio.msg_node.unsubscribe(mb_protocol.SYS_NODE_DISCONNECT+'.Engine', 
                                            self.msg_eng_change)
        self.fileio.msg_node.unsubscribe(eng_messages.ENGINE_STATE_CHANGE,
                                        self.msg_eng_change)
        self.fileio.msg_node.unsubscribe(eng_messages.ENGINE_STATE_DONE, 
                                        self.msg_eng_change)

    #---interfaces--------------------------------------------------------------
    def RefreshNameList(self):
        self.list.DeleteAllItems()
        names = self.names
        self.names = {}
        for name in names.keys():
            self.AddName(name)

    def RefreshTree(self):
        self.tree.DeleteChildren(self.root)
        eng = self.console.get_engine_console(self.engname)
        self.tree.SetItemHasChildren(self.root, True)
        if eng is None:
            self.tree.SetItemHasChildren(self.root, False)
        self._AddChildren(self.root)

    def AddName(self,address, type_string=None):
        """Add a name to the list to be exported"""
        #check if already in the list
        if address in self.names:
            return
        eng = self.console.get_engine_console(self.engname)
        if eng is None:
            return

        #check the object exists
        if eng.run_task('object_exists',(address,)) is False:
            return
        #get type_string if not provided.
        if type_string is None:
            type_string =eng.run_task('get_type_string', (address,))

        icon = self._GetTypeIconIndex(type_string)
        n = self.list.GetItemCount()
        index = self.list.InsertImageStringItem(n, address, icon)
        self.list.SetStringItem(index, 1,type_string)
        self.names[address] = type_string
 
        #grey out it not supported by the exporter.
        if (type_string not in self.types) and (-1 not in self.types):
            self.list.SetItemTextColour(n,'GREY')

    def SetEngine(self, engname):
        """
        Set the engine to use.
        """
        self.engnames = self.console.get_engine_names()
        if engname not in self.engnames:
            raise NameError('No engine with name: '+engname)        
        if self.engname == engname:
            #if engine has not changed do nothing
            return

        #tree
        self.engname = engname
        self.tree.SetItemText(self.root,self.engname)
        self.RefreshTree()
        #name list
        self.names = {}
        self.RefreshNameList()
        #choice list
        labels = self.console.get_engine_labels()
        self.englist.SetItems(labels)
        self.englist.SetSelection(self.engnames.index(self.engname))

    def SetTypeFilter(self, type_strings):
        """
        Set the object type filters - type_string is a tuple/list of types that
        are valid selectable objects. Objects whose types are not in the list 
        are shown in grey.
        Each type is a string of 'module.name' or -1 (used in the list to allow
        all types).
        """
        self.types = type_strings
        #refesh tree and list
        self.RefreshTree()
        self.RefreshNameList()

    def GetObjectNames(self):
        """
        Get a list of object names to export
        """
        return self.names.keys()

    #---internal methods--------------------------------------------------------
    def _AddChildren(self, item):
        self.tree.DeleteChildren(item)
        address,type_string = self.tree.GetPyData(item)
        #get dir listing
        eng = self.console.get_engine_console(self.engname)
        if eng is None:
            return
        names = eng.evaluate('dir('+address+')')
        #add children
        for name in names:
            #get object address
            if address == '':
                child_address = name
            else:
                child_address = address+'.'+name
            type_string = eng.run_task('get_type_string', (child_address,))
            icon_index = self._GetTypeIconIndex(type_string)
            data=wx.TreeItemData((child_address, type_string))
            child = self.tree.AppendItem(parent=item, text=name, image=icon_index, data=data)
            self.tree.SetItemHasChildren(child, True)
            #check types string
            if (type_string not in self.types) and (-1 not in self.types):
                self.tree.SetItemTextColour(child, 'GREY')

    def _GetTypeIconIndex(self, type_string):
        # get icon index
        if self.idict.has_key(type_string):
            #from dictionary
            icon_index = self.idict[type_string]
        else:
            #add new icon
            icon = self.nsbtool.get_type_icon(type_string)
            if icon is None:
                #use default
                icon_index = self.idict[-1]
            else:
                icon_index = self.il.AddIcon(icon)
            self.idict[type_string] = icon_index
        return icon_index

    #---events------------------------------------------------------------------
    def OnEngineChoice(self,event):
        n = event.GetSelection()
        self.SetEngine(self.engnames[n])

    def OnExporterChoice(self,event):
        n = event.GetSelection()
        if n is None:
            self.exporter = None
            self.descrip.SetLabel( 'Select an exporter above.' )
        else:
            self.exporter = self.exporters[n]
            self.SetTypeFilter( self.exporter.get_types() )
            self.descrip.SetLabel( self.exporter.get_description() )
        
    def OnItemExpanding(self, event):
        """Add children to the tree item."""
        busy = wx.BusyCursor()
        item = event.GetItem()
        if self.tree.IsExpanded(item):
            return
        self._AddChildren(item)

    def OnAdd(self,event):
        #get selected item from tree control.
        treeids = self.tree.GetSelections()
        for treeid in treeids:
            address,type_string = self.tree.GetPyData(treeid)
            self.AddName(address, type_string)

    def OnRemove(self,event):
        n = self.list.GetFirstSelected()
        while n!=-1:
            address = self.list.GetItemText(n)
            self.list.DeleteItem(n)
            self.names.pop(address)
            n = self.list.GetFirstSelected(n)
    
    def OnClear(self,event):
        self.list.DeleteAllItems()
        self.names = []

    def OnNext(self,event):
        if self.exporter is None:
            return
 
        #no objects selected
        if len(self.names)==0:
            msg = "No objects selected to export"
            dlg = wx.MessageDialog(self, msg,
            "Select objects",wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        #check for valid names
        valid = True
        msg = "Some objects cannot be exported using the selected exporter:"
        for name in self.names:
            type_string = self.names[name]
            if (type_string not in self.types) and (-1 not in self.types):
                msg = msg +'\n\t'+name
                valid = False

        if valid is True:
            event.Skip()
            return
        
        dlg = wx.MessageDialog(self, msg,
            "Incompatiable object type for exporter",wx.OK|wx.ICON_EXCLAMATION)
        dlg.ShowModal()
        dlg.Destroy()

    #---messages----------------------------------------------------------------
    def msg_eng_change(self,msg):
        """Message handler for Engine.Done and Engine.StateChange"""
        engname,debug,profile = msg.get_data()
        if engname == self.engname:
            self.RefreshTree()

#-------------------------------------------------------------------------------
# A standard panel to handle generating multiple filenames when exporting 
# multiple objects
#-------------------------------------------------------------------------------
class ObjectsToMultipleFilesPanel(wx.Panel):
    def __init__(self,parent,engname, onames):
        """
        A panel to handle the selection of multiple filepaths for multiple 
        python objects.
        engname = engine name to export objects from. 
        onames  = list of object names to export.
        """
        wx.Panel.__init__(self, parent, -1)

        #get references to required core tools.
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')
        self.nsbtool = app.toolmgr.get_tool('NSBrowser')

        #attributes
        self.engname = engname
        self.onames  = onames
        self.ext = ''
        self.filenames = []

        self._InitControls()
        #populate name list
        self._DoAutoName()
        self._RefreshList()

    def _InitControls(self):
        #box sizer
        box = wx.StaticBox(self, -1, "Export to multiple files:")
        boldfont = box.GetFont()
        boldfont.SetWeight(wx.BOLD)
        box.SetFont(boldfont)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.SetSizer(bsizer)

        #add dir selection box
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self, -1, 'Destination path:', size=(150,-1))

        #get the starting path
        eng = self.console.get_engine_console(self.engname)
        path = eng.run_task('get_cwd')
        hsizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.dirpicker = wx.DirPickerCtrl( self, -1, 
                    path=path,
                    message='Select directory:',
                    style=wx.DIRP_DEFAULT_STYLE,
                    size = (300,-1)
                    )
        hsizer.Add(self.dirpicker,1,wx.EXPAND|wx.ALL,5)
        bsizer.Add(hsizer, 0, wx.EXPAND|wx.ALL,0)

        #names list
        self.list = EditListCtrl(self, -1, 
                                style=wx.LC_REPORT 
                                 | wx.BORDER_SUNKEN
                                 | wx.LC_HRULES)
        self.list.InsertColumn(0, 'Object', width=130)
        self.list.InsertColumn(1, 'Filename', width=130)
        self.list.SetColumnEditable(1,True)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnListEdit, self.list)
        bsizer.Add(self.list, 1, wx.EXPAND|wx.ALL,5)

        #set up an image list to use for type icons
        self.il =  wx.ImageList(22, 22)
        self.idict = {} #typestring:icon index
        icon = self.nsbtool.get_type_icon(-1)        #add default icon
        self.idict[-1] = self.il.AddIcon(icon)
        self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        #automatic nameing.
        self.autocheck = wx.CheckBox(self,-1,'Automatically name files')
        self.autocheck.SetValue(False)
        self.Bind(wx.EVT_CHECKBOX, self.OnAutoName, self.autocheck)
        bsizer.Add(self.autocheck,0,wx.ALL,5)

        #autoname panel
        self.autoname_panel = wx.Panel(self,-1)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.autoname_panel.SetSizer(vsizer)
        bsizer.Add(self.autoname_panel,0,wx.EXPAND|wx.ALL,5)
        self.autoname_panel.Hide()

        #autoname panel - name format
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self.autoname_panel, -1, 'File name format:', size=(150,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.name = wx.TextCtrl(self.autoname_panel,-1, '<objname>', size=(150,-1))
        hsizer.Add(self.name,1,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.Bind(wx.EVT_TEXT, self.OnName, self.name)
        self.help = wx.Button( self.autoname_panel, -1, '?')
        self.Bind(wx.EVT_BUTTON, self.OnHelp, self.help) 
        hsizer.Add(self.help,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        vsizer.Add(hsizer,0,wx.EXPAND|wx.ALL,0)

        #autoname panel - object counter
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.autoname_panel,-1,'Start counter at:', size=(150,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.count = wx.TextCtrl(self.autoname_panel,-1, '0', size=(100,-1)) #TODO: change to IntCtrl/FloatCtrl
        hsizer.Add(self.count,0,wx.ALL,5)
        label = wx.StaticText(self.autoname_panel,-1,'Increment by:', size=(150,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.count_inc = wx.TextCtrl(self.autoname_panel,-1, '1',size=(100,-1))
        hsizer.Add(self.count_inc,0,wx.ALL,5)
        vsizer.Add(hsizer,0,wx.EXPAND|wx.ALL,0)

    def _RefreshList(self):
        self.list.DeleteAllItems()
        #get the engine to use
        eng = self.console.get_engine_console( self.engname )
        if eng is None:
            return

        for n in range(0, len(self.onames)):
            name = self.onames[n]
            filename = self.filenames[n]
            #add to the list control
            type_string = eng.run_task('get_type_string', (name,))
            icon = self._GetTypeIconIndex(type_string)
            index = self.list.InsertImageStringItem(n, name, icon)
            self.list.SetStringItem(index, 1,filename)

    def _DoAutoName(self):
        format = self.name.GetValue()
        #get the counter start and increament.
        counter = int(self.count.GetValue())
        inc     = int(self.count_inc.GetValue())

        #get the data and time stamps
        timestamp = time.localtime()
        names = []
        for name in self.onames:
            name = format.replace('<objname>',name)
            name = name.replace('<engname>',self.engname)
            name = name.replace('<counter>', str(counter))

            #time and date
            name = name.replace('<Y>', time.strftime('%y', timestamp))      #10
            name = name.replace('<YY>', time.strftime('%Y', timestamp))     #2010
            name = name.replace('<M>', time.strftime('%m', timestamp))      #10
            name = name.replace('<MM>', time.strftime('%b', timestamp))     #Oct
            name = name.replace('<MMM>', time.strftime('%B', timestamp))    #October
            name = name.replace('<D>', time.strftime('%d', timestamp))      #17
            name = name.replace('<DD>', time.strftime('%a', timestamp))     #Sun
            name = name.replace('<DDD>', time.strftime('%A', timestamp))    #Sunday
            name = name.replace('<h>', time.strftime('%H', timestamp))      #21
            name = name.replace('<m>', time.strftime('%M', timestamp))      #45
            name = name.replace('<s>', time.strftime('%S', timestamp))      #12
            name = name.replace('<date>',time.strftime('%x', timestamp))    #17/10/10
            name = name.replace('<time>',time.strftime('%X', timestamp))    #21:45:12

            name,ext = os.path.splitext(name)
            #no extension use default
            if ext=='':
                ext = '.'+self.ext
            # add default - but only if not empty
            if ext!='':
                name = name+ext
            #store name
            names.append(name)
            #increament object counter
            counter = counter + inc
        self.filenames = names

    def _GetTypeIconIndex(self, type_string):
        # get icon index
        if self.idict.has_key(type_string):
            #from dictionary
            icon_index = self.idict[type_string]
        else:
            #add new icon
            icon = self.nsbtool.get_type_icon(type_string)
            if icon is None:
                #use default
                icon_index = self.idict[-1]
            else:
                icon_index = self.il.AddIcon(icon)
            self.idict[type_string] = icon_index
        return icon_index

    #---interfaces--------------------------------------------------------------
    def SetExtension(self, ext):
        """
        Set the file extension to use when automatically naming files.
        """
        self.ext = ext
        if self.autocheck.GetValue() is True:
            self._DoAutoName()
        else:
            #update filenames as the extension has changed
            names = []
            for name in self.filenames:
                #remove old extenstion
                name = os.path.splitext(name)[0]
                if ext!='':
                    name = name+'.'+self.ext
                    names.append(name)    
            self.filenames = names
        self._RefreshList()

    def GetFilenames(self):
        """
        Get a list of filenames
        """
        #refresh autonames if needed
        if self.autocheck.GetValue() is True:
            self._DoAutoName()
        return self.filenames

    def GetFilepaths(self):
        """
        Get a list of filepaths
        """
        filenames = self.GetFilenames()
        path = self.dirpicker.GetPath()

        filepaths = [] 
        for name in filenames:
            filepath = path+os.sep+name
            filepaths.append(filepath)
        return filepaths
    
    #---events------------------------------------------------------------------
    def OnHelp(self, event):
        msg = 'The following strings can be used to automatically insert name elements use:\n\n'
        msg = msg+'<objname> \t to insert object name\n'
        msg = msg+'<engname> \t to insert engine name\n'
        msg = msg+'<counter> \t to insert object counter\n'
        msg = msg+'<date>    \t to insert date\n'
        msg = msg+'<time>    \t to insert timestamp\n'
        msg = msg+'<Y>,<YY> \t to insert year (eg. 10 , 2010)\n'
        msg = msg+'<M>, <MM>, <MMM> \t to insert month (eg. 10 , Oct or October)\n'
        msg = msg+'<D>, <DD>, <DDD> \t to insert day (eg. 17 , Sun or Sunday)\n'
        msg = msg+'<h>, <m>, <s> \t to insert time (hours, minutes, seconds)\n\n'
        msg = msg+'Other characters will be included as typed.\n'
        wx.MessageBox(msg,'File name help', style=wx.HELP|wx.CENTRE, parent=self)

    def OnAutoName(self, event):
        state = event.IsChecked()
        self.autoname_panel.Show(state)
        self.Layout()
        #populate name list
        format = self.name.GetValue()
        if state:
            self._DoAutoName()
            self._RefreshList()
            self.list.SetColumnEditable(1,False)
        else:
            self.list.SetColumnEditable(1,True)

    def OnName(self, event):
        if self.autocheck.GetValue() is True:
            self._DoAutoName()
            self._RefreshList()

    def OnListEdit(self, event):
        #store changed name back to filenames
        self.filenames[event.m_itemIndex] = event.GetText()

#-------------------------------------------------------------------------------
# A standard panel to handle generating a signle filename and allowing automatic
# name elements to be inserted (date/time etc)
#-------------------------------------------------------------------------------
class ObjectsToSingleFilePanel(wx.Panel):
    def __init__(self,parent,engname, onames):
        """
        A panel to handle the selection of a single filepath.
        engname = engine name to export objects from. 
        onames  = list of object names to export.
        """
        wx.Panel.__init__(self, parent, -1)

        #get references to required core tools.
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #attributes
        self.engname = engname
        self.onames  = onames
        self.ext = ''
        self.filename = 'data'

        self._InitControls()
        self._DoAutoName()

    def _InitControls(self):

        #box sizer
        box = wx.StaticBox(self, -1, "Export to file:")
        boldfont = box.GetFont()
        boldfont.SetWeight(wx.BOLD)
        box.SetFont(boldfont)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.SetSizer(bsizer)

        #add dir selection box
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self, -1, 'Destination path:', size=(150,-1))
        #get the starting path
        eng = self.console.get_engine_console(self.engname)
        path = eng.run_task('get_cwd')
        hsizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.dirpicker = wx.DirPickerCtrl( self, -1, 
                    path=path,
                    message='Select directory:',
                    style=wx.DIRP_DEFAULT_STYLE,
                    size = (300,-1)
                    )
        hsizer.Add(self.dirpicker,1,wx.EXPAND|wx.ALL,5)
        bsizer.Add(hsizer, 0, wx.EXPAND|wx.ALL,0)

        #name
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self, -1, 'File name format:', size=(150,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.name = wx.TextCtrl(self,-1, self.filename, size=(150,-1))        
        self.Bind(wx.EVT_TEXT, self.OnName, self.name)
        hsizer.Add(self.name,1,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.help = wx.Button( self, -1, '?')
        self.Bind(wx.EVT_BUTTON, self.OnHelp, self.help) 
        hsizer.Add(self.help,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        bsizer.Add(hsizer,0,wx.EXPAND|wx.ALL,0)

        #example name
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( self, -1, 'Example filename:', size=(150,-1))
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.example = wx.TextCtrl(self,-1, self.filename, style=wx.TE_READONLY)
        hsizer.Add(self.example,1,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        bsizer.Add(hsizer,0,wx.EXPAND|wx.ALL,0)

 
    def _DoAutoName(self):

        #get the data and time stamps
        timestamp = time.localtime()
        name = self.name.GetValue()
        name = name.replace('<engname>',self.engname)

        #time and date
        name = name.replace('<Y>', time.strftime('%y', timestamp))      #10
        name = name.replace('<YY>', time.strftime('%Y', timestamp))     #2010
        name = name.replace('<M>', time.strftime('%m', timestamp))      #10
        name = name.replace('<MM>', time.strftime('%b', timestamp))     #Oct
        name = name.replace('<MMM>', time.strftime('%B', timestamp))    #October
        name = name.replace('<D>', time.strftime('%d', timestamp))      #17
        name = name.replace('<DD>', time.strftime('%a', timestamp))     #Sun
        name = name.replace('<DDD>', time.strftime('%A', timestamp))    #Sunday
        name = name.replace('<h>', time.strftime('%H', timestamp))      #21
        name = name.replace('<m>', time.strftime('%M', timestamp))      #45
        name = name.replace('<s>', time.strftime('%S', timestamp))      #12
        name = name.replace('<date>',time.strftime('%x', timestamp))    #17/10/10
        name = name.replace('<time>',time.strftime('%X', timestamp))    #21:45:12

        name,ext = os.path.splitext(name)
        #no extension use default
        if ext=='':
            ext = '.'+self.ext
        # add default - but only if not empty
        if ext!='':
            name = name+ext
        self.filename = name

    #---interfaces--------------------------------------------------------------
    def SetExtension(self, ext):
        """
        Set the file extension to use when automatically naming files.
        """
        self.ext = ext
        name = self.name.GetValue()
        name,ext = os.path.splitext( name )
        name = name+'.'+self.ext
        self.name.SetValue(name)
        self._DoAutoName()

    def GetFilename(self):
        """
        Get the filename
        """
        self._DoAutoName()
        return self.filename

    def GetFilepath(self):
        """
        Get the filepath
        """
        filename = self.GetFilename()
        path = self.dirpicker.GetPath()
        filepath = path+os.sep+filename
        return filepath
    
    def SetFilename(self, filename):
        """
        Set the filename
        """
        self.filename = filename
        ext = os.path.splitext(filename)[1]
        self.ext = ext
        self.name.SetValue(self.filename)

    #---events------------------------------------------------------------------
    def OnHelp(self, event):
        msg = 'The following strings can be used to automatically insert name elements use:\n\n'
        msg = msg+'<engname> \t to insert engine name\n'
        msg = msg+'<date>    \t to insert date\n'
        msg = msg+'<time>    \t to insert timestamp\n'
        msg = msg+'<Y>,<YY> \t to insert year (eg. 10 , 2010)\n'
        msg = msg+'<M>, <MM>, <MMM> \t to insert month (eg. 10 , Oct or October)\n'
        msg = msg+'<D>, <DD>, <DDD> \t to insert day (eg. 17 , Sun or Sunday)\n'
        msg = msg+'<h>, <m>, <s> \t to insert time (hours, minutes, seconds)\n\n'
        msg = msg+'Other characters will be included as typed.\n'
        wx.MessageBox(msg,'File name help', style=wx.HELP|wx.CENTRE, parent=self)

    def OnName(self, event):
        self._DoAutoName()
        self.example.SetValue(self.filename)

#-------------------------------------------------------------------------------
# A standard dialog to handle exporting multiple objects to individual files
#-------------------------------------------------------------------------------
class MultipleObjectToFileDialog(wx.Dialog):
    def __init__(self,parent, engname, onames, exts=['dat'], ext_descrips = ['data'],ext_multi=[True]):
        """
        Create a dialog for exporting to multiple files.
        engname = engine name to export objects from. 
        onames  = list of object names to export.
        ext_descrips   = list of extension descriptions
        exts = list of extensions
        ext_multi  = lsit of True/False flags indicating whether to use  the
        single file or multi-file panel for the extension.
        """
        wx.Dialog.__init__(self,parent,-1,title='Export multiple objects to file',
                            style=wx.DEFAULT_DIALOG_STYLE| wx.RESIZE_BORDER,
                            size=(720,420))

        #get references to required core tools.
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #attributes
        self.engname = engname
        self.onames  = onames
        self.opt_dialog = None
        self.filepaths = []
        self.options = {} #dict of ext string: options dialog

        #get extensions
        self.ext_descrips = ext_descrips
        self.exts = exts
        self.ext_multi = ext_multi
        self.multi = True #return multiple filepaths

        #controls
        self._InitControls()

    def _InitControls(self):
        dsizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(self,-1)
        psizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(psizer)
        dsizer.Add( panel, 1, wx.EXPAND,0)

        #multi file panel
        self.multi_panel = ObjectsToMultipleFilesPanel(panel, self.engname, self.onames)
        self.multi_panel.SetExtension( self.exts[0])
        psizer.Add( self.multi_panel, 1, wx.EXPAND|wx.ALL,10)

        #single file panel
        self.single_panel = ObjectsToSingleFilePanel(panel, self.engname, self.onames)
        self.single_panel.SetExtension( self.exts[0])
        psizer.Add( self.single_panel, 1, wx.EXPAND|wx.ALL,10)

        #file type panel
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText( panel, -1, 'Export as:')
        hsizer.Add(label,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.ext_choice = wx.Choice(panel,-1, size=(200,-1), choices= self.ext_descrips)
        self.ext_choice.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnExtChanged, self.ext_choice)
        hsizer.Add(self.ext_choice,0,wx.ALIGN_CENTER_VERTICAL|wx.ALL,5)
        self.opt_but = wx.Button(panel, -1, 'Options')
        hsizer.AddStretchSpacer(1)
        hsizer.Add(self.opt_but,0,wx.ALIGN_RIGHT|wx.ALL,5)
        self.opt_but.Hide()
        self.Bind(wx.EVT_BUTTON, self.OnOptions, self.opt_but)
        psizer.Add(hsizer,0,wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT,5)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        dsizer.Add(line,0,wx.EXPAND|wx.ALL,5)
        next_but    = wx.Button(self, wx.ID_OK, "OK")
        cancel_but= wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        butsizer.Add( next_but, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT,5)
        butsizer.Add( cancel_but, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT,5)
        dsizer.Add(butsizer,0, wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM,5)
        self.SetSizer(dsizer)

        #hide the multi or single file panel
        if self.ext_multi[0]:
            self.single_panel.Hide()
            self.multi=True
        else:
            self.multi_panel.Hide()
            self.multi=False
        self.psizer=psizer
        self.psizer.Layout()

    #---Interfaces--------------------------------------------------------------
    def SetOptionsDialog(self, ext, opt_dialog):
        """
        Set the options dialog to display
        """
        self.options[ext] = opt_dialog
        #check current if this is the current ext and show options button if it 
        #is
        n = self.ext_choice.GetSelection()
        if ext == self.exts[n]:
            self.opt_but.Show()
            self.Layout()

    def GetOptionsDialog(self):
        """
        Returns the options dialog or None
        """
        return self.opt_dialog

    def GetFilenames(self):
        """
        Returns a list of filenames
        """
        if self.multi:
            names = self.multi_panel.GetFilenames()
        else:
            names = [self.single_panel.GetFilename()]
        return names

    def GetFilepaths(self):
        """
        Returns a list of filepaths
        """
        if self.multi:
            paths = self.multi_panel.GetFilepaths()
        else:
            paths = [self.single_panel.GetFilepath()]
        return paths

    def GetExt(self):        
        n = self.ext_choice.GetSelection()
        return self.exts[n]

    def GetExtIndex(self):
        """
        Returns the index to the extension/type choice selected
        Usefull if several types have same extension!
        """
        return self.ext_choice.GetSelection()

    #---events------------------------------------------------------------------
    def OnOptions(self, event):
        n = self.ext_choice.GetSelection()
        ext = self.exts[n]
        d = self.options[ext]
        d.ShowModal()

    def OnExtChanged(self,event):
        n = self.ext_choice.GetSelection()

        #hide/show multi/single file panels
        if self.ext_multi[n]:
            self.single_panel.Hide()
            self.multi_panel.Show()
            self.multi=True
        else:    
            self.single_panel.Show()
            self.multi_panel.Hide()
            self.multi=False

        self.multi_panel.SetExtension(self.exts[n])
        self.single_panel.SetExtension(self.exts[n])

        #show options button if options dialog is set for extension.
        if self.options.has_key(self.exts[n]):
            self.opt_but.Show()
        else:
            self.opt_but.Hide()
        self.Layout()
        self.psizer.Layout()

