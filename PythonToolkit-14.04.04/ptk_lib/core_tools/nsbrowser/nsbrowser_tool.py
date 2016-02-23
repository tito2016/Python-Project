"""
Namespace browser

A matlab style namespace browser
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import wx
import wx.aui as aui

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode

from ptk_lib.core_tools.console import console_messages

import nsb_icons
import nsb_tasks
import nsb_messages
from nsb_control import NSBrowserControl

import type_icons
import type_infos
from type_actions import Action, BrowseToAction

#---the tools class-------------------------------------------------------------
class NamespaceBrowser(Tool):
    name = 'NSBrowser'
    descrip = 'Core tool implementing a ''matlab style'' namespace browser'  
    author = 'T.Charrett' 
    requires = ['Console'] #required before init.
    core = True
    icon = nsb_icons.nsbrowser32

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #store registered type icons, info callable and actions
        self.type_icons = {} #{type_string:icon}
        self.type_infos = {} #{type_string:info callable}

        #dictionary of registered python type actions {name:Action object}
        self.type_actions = {}

        #register standard icons/infos/actions
        self._register_standard_icons()
        self._register_standard_infos()
        self.register_type_action( BrowseToAction(self) )

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('NSBrowser')
        self.msg_node.connect(self.msg_bus)

        #Register message handlers
        self.msg_node.set_handler(nsb_messages.SHOW,      self.msg_show) 
        self.msg_node.set_handler(nsb_messages.BROWSE_TO, self.msg_browse_to)

        #subscribe to messages
        self.msg_node.subscribe('App.Init',self.msg_app_init)
        self.msg_node.subscribe('App.Exit',self.msg_app_exit)

        #create the namespace browser
        self.console = self.toolmgr.get_tool('Console')
        self.nsbrowser = NSBrowserControl(self.console.frame, self)

        #add to the console frame aui manager
        pane = aui.AuiPaneInfo()
        name='Namespace Browser'
        pane.Name(name)
        pane.Caption(name)
        pane.Top()
        #pane.Position(0)
        pane.CloseButton(True)
        pane.MaximizeButton(True)
        pane.MinimizeButton(True)
        pane.Floatable(True)
        pane.BestSize( (490,200) )
        pane.MinSize( (490,200))
        pane.DestroyOnClose(False)
        self.console.frame.auimgr.AddPane(self.nsbrowser,pane)
        pane.Hide()

        #add a menu item to the tools menu to show and hide our pane
        bmp = nsb_icons.nsbrowser16.GetBitmap()
        self.console.add_menu_item('tools', wx.NewId(), 'Namespace Browser', 
                    'Open the Namespace Browser pane', self.on_show, bmp)

        log.info('Done Initialising tool')

    #---init tasks--------------------------------------------------------------
    def _register_standard_icons(self):
        """
        Register the default icon set
        """
        #icon used for all other types
        self.set_type_icon(-1,type_icons.obj_icon.GetIcon())

        #standard data types (instances of)
        self.set_type_icon('__builtin__.bool' , type_icons.bol_icon.GetIcon())
        self.set_type_icon('__builtin__.int'  , type_icons.int_icon.GetIcon())
        self.set_type_icon('__builtin__.long' , type_icons.long_icon.GetIcon())
        self.set_type_icon('__builtin__.float' , type_icons.flt_icon.GetIcon())
        self.set_type_icon('__builtin__.complex' , type_icons.comp_icon.GetIcon())
        self.set_type_icon('__builtin__.str' , type_icons.str_icon.GetIcon())
        self.set_type_icon('__builtin__.unicode' , type_icons.unicode_icon.GetIcon())
        self.set_type_icon('__builtin__.file' , type_icons.file_icon.GetIcon())
        self.set_type_icon('__builtin__.dict' , type_icons.dict_icon.GetIcon())
        self.set_type_icon('__builtin__.list' , type_icons.list_icon.GetIcon())
        self.set_type_icon('__builtin__.tuple' , type_icons.tup_icon.GetIcon())
        self.set_type_icon('__builtin__.NoneType' , type_icons.none_icon.GetIcon())
        self.set_type_icon('__builtin__.module' , type_icons.mod_icon.GetIcon())
        
        #classes/types
        self.set_type_icon('__builtin__.classobj' , type_icons.cla_icon.GetIcon())
        self.set_type_icon('__builtin__.type' , type_icons.cla_icon.GetIcon())
        self.set_type_icon('__builtin__.object' , type_icons.cla_icon.GetIcon())
        
        #functions/methods
        self.set_type_icon('__builtin__.function' , type_icons.fnc_icon.GetIcon())
        self.set_type_icon('__builtin__.builtin_function_or_method' , type_icons.fnc_icon.GetIcon())
        self.set_type_icon('__builtin__.ufunc' , type_icons.fnc_icon.GetIcon())
        self.set_type_icon('__builtin__.instancemethod' , type_icons.mth_icon.GetIcon())
    
    def _register_standard_infos(self):
        self.set_type_info(-1, type_infos.infovalue)

    #---interfaces--------------------------------------------------------------
    #type icons - set the icon to display for python types in the NSBrowser
    def set_type_icon(self,type_string, icon):
        """
        Set an icon for an object type.

        type_string is a string e.g. 'package.module.type' or 'module.type'
        icon is a wx.Bitmap of size=22x22 pixels.

        Returns True if successfull, false if an icon is already registered
        """
        #check if there is already an icon for the type
        if self.type_icons.has_key(type_string):
            return False
        self.type_icons[type_string] = icon
        return True
    
    def get_type_icon(self,type_string):
        """
        Get the type icon for an object type.

        type_string is a string 'package.module.type' or 'module.type'
        Returns None if no icon registered.
        Use type_string -1 to return the default icon.
        """
        return self.type_icons.get(type_string, None )

    #python object filtering 
    def set_filter_overides(self,type_string, flags):
        """
        Set the filter flags to use for objects of the type given .
        flags = (istype,isrout,ismod,isinst) filter flags

        - for example this allows numpy.ufunc to appear as routines.
            type_string = 'numpy.ufunc'
            flags = (False,True,False,False) filter flags
        """
        self.list.SetFilterOverride(type_string,flags)

    #type actions - add actions that can be perform on python objects
    def register_type_action(self,action):
        """
        Register an Action object with the namespace browser. This is shown in
        context menus for the object types given in action.type_strings. 
        Use type_string=-1 to register for all object types. 
        action.multi=True/False determines if this action should be displayed 
        when multiple objects are selected.
        """
        if isinstance(action, Action) is False:
            raise Exception('Expected an Action object!')
        self.type_actions[action.address] = action 

    def get_type_actions(self,type_strings):
        """
        Get the actions for the object type. 

        This returns a dict of possible actions that can handle the type
        given by type_strings.
        """
        actions = {}
        for action in self.type_actions.values():
            if action.can_handle(type_strings) is True:
                actions[action.address]=action
        return actions

    #type info callable - set the text string that appears in the info/value column
    def set_type_info(self, type_string, call):
        """
        Set a callable to fetch the text string that appears in the info/value  
        column of the NSBrowser. The callable should take an engine interface 
        instance and object name string as arguments and return a string.

        Returns True if sucessfull, False if an info callable is already 
        registered for the python type.
        """
        #check if there is already an icon for the type
        if self.type_infos.has_key(type_string):
            return False
        self.type_infos[type_string] = call
        return True

    def get_type_info(self, type_string):
        """
        Get the callable to fetch the text string that appears in the info/value
        column of the NSBrowser. The callable takes an engine interface instance
        and object name string as arguments and returns a string. Returns None 
        if no callable has been registered.
        """
        return self.type_infos.get( type_string, None )
    
    def browse_to(self,engname, oname):
        """
        Browse to the object given in the nsbrowser.
        """
        self.nsbrowser.SetAddress(oname, engname)
        #make sure nsbrowser is visable
        pane=self.console.frame.auimgr.GetPane('Namespace Browser')
        pane.Show()
        self.console.frame.auimgr.Update()

    #---Message handlers--------------------------------------------------------
    def msg_app_init(self,msg):
        """
        On application start load the settings
        """
        #load the filter settings
        cfg = self.app.GetConfig()
        self.nsbrowser.list.show_mod = cfg.ReadBool("NSBrowser//show_mod",True)
        self.nsbrowser.list.show_types = cfg.ReadBool("NSBrowser//show_types", True)
        self.nsbrowser.list.show_inst = cfg.ReadBool("NSBrowser//show_inst", True)
        self.nsbrowser.list.show_func = cfg.ReadBool("NSBrowser//show_call", True)
        self.nsbrowser.list.show_hidden = cfg.ReadBool("NSBrowser//show_hidden", False)

    def msg_app_exit(self,msg):
        """
        On application exit save the settings
        """
        #save filter settings
        cfg = self.app.GetConfig()
        cfg.WriteBool("NSBrowser//show_mod", self.nsbrowser.list.show_mod)
        cfg.WriteBool("NSBrowser//show_types", self.nsbrowser.list.show_types)
        cfg.WriteBool("NSBrowser//show_inst", self.nsbrowser.list.show_inst)
        cfg.WriteBool("NSBrowser//show_call", self.nsbrowser.list.show_call)
        cfg.WriteBool("NSBrowser//show_hidden", self.nsbrowser.list.show_hidden)
        cfg.Flush() #needed to ensure data is writen to file.

    def msg_show(self,msg):
        """
        Message handler for NSBrowser Show and wxEvent handler for menu.
        Shows the NSBrowser pane.
        """
        pane=self.console.frame.auimgr.GetPane('Namespace Browser')
        pane.Show()
        self.console.frame.auimgr.Update()

    def msg_browse_to(self,msg):
        """
        Message handler for NSBrowser BrowseTo.
        Display the namespace of the object given by data=(engname,oname).
        """
        #change address
        engname,oname = msg.get_data()
        self.browse_to(engname,oname)

    #---other-------------------------------------------------------------------
    def on_show(self,msg_or_event):
        """
        wxEvent handler for menu, shows the NSBrowser pane.
        """
        pane=self.console.frame.auimgr.GetPane('Namespace Browser')
        pane.Show()
        self.console.frame.auimgr.Update()
