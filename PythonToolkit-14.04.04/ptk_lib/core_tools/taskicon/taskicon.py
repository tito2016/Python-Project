"""
Tool providing a taskbar/notification area icon and extendable settings dialog
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---imports---------------------------------------------------------------------
import wx

from ptk_lib import VERSION
from ptk_lib.tool_manager import Tool
from ptk_lib.resources import ptk_icons
from ptk_lib.message_bus.mb_node import MBLocalNode

from settings_dialog import SettingsDialog
from tool_settings import ToolManagerPanel
from app_settings import AppSettingsPanel

#-------------------------------------------------------------------------------
class TaskIcon(Tool):
    name = 'TaskIcon'
    descrip = 'Core tool providing taskbar icon and settings dialog'
    author = 'T.Charrett'
    requires = []           
    core = True            
    icon = None    
         
    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        #add taskbar icon
        self.icon = PTKTaskBarIcon(self)

        #additional panels for the settings dialog
        self.settings_panels = []
        self.bitmaps = {None:-1} #ditc of {bitmap:number}
        self.imagelist = wx.ImageList(16, 16)

        #general application settings page
        self.add_settings_item('Application settings',None, ptk_icons.ptkicon16.GetBitmap())
        self.add_settings_item('Application settings\\Message port',AppSettingsPanel, None)
        self.add_settings_item('Application settings\\Tools',ToolManagerPanel, None)

        #create a message bus node for this tool
        self.msg_node = MBLocalNode('TaskIcon')
        self.msg_node.connect(self.msg_bus)
        
        self.msg_node.set_handler('Settings.Show', self.msg_settings_show)
        self.msg_node.subscribe('App.Exit', self.msg_app_exit)

        log.info('Tool initialised')

    #---message handlers--------------------------------------------------------
    def msg_app_exit(self,msg):
        #remove icon
        log.info('Removing taskbar icon')
        self.icon.RemoveIcon()

    def msg_settings_show(self,msg):
        self.show_settings()

    #---Interfaces--------------------------------------------------------------
    def add_menu_item(self, id, string, helpstring, evthndlr, bitmap=None, pos=None):
        """
        Add a menu item to the taskbar menu.
            string -   string to add
            helpstring - help string for item
            evthndlr - wx event handler callable
            bitmap  - bitmap to use / None for no bitmap
            pos - Position in menu, inserted here if specified.
        """
        item = wx.MenuItem(self.icon.menu, id, string,helpstring)
        self.icon.Bind(wx.EVT_MENU, evthndlr, id=id)
        if bitmap is not None:
            item.SetBitmap(bitmap)
        if pos is None:
            pos = self.icon.menu.GetMenuItemCount() - 2
        self.icon.menu.InsertItem(pos,item)  

    def show_settings(self):
        """
        Show the settings dialog
        """
        #create the dialog
        dialog = SettingsDialog(self.settings_panels, self.imagelist)
        val = dialog.ShowModal()
        if val == wx.ID_OK:
            dialog.SaveSettings()
        dialog.Destroy()

    def add_settings_item(self,address, panel_class, bitmap=None):
        """
        Add a settings panel to the dialog notebook.
            address - location address for panel
            panel  - wxPanel class, should take parent as argument and have SaveSetting/LoadSettings methods
            bitmap  - wxImage to display in tree.
        """
        #get bitmap index
        if self.bitmaps.has_key(bitmap):
            index = self.bitmaps[bitmap]
        else:
            index = self.imagelist.Add(bitmap)
            self.bitmaps[bitmap] = index

        #no dialog yet - add to list of panels to create
        self.settings_panels.append( (address, panel_class, index) )



"""
The python toolkit taskbar icon
"""
#---Imports---------------------------------------------------------------------


#---task bar icon---------------------------------------------------------------
class PTKTaskBarIcon(wx.TaskBarIcon):
    def __init__(self, tool):
        wx.TaskBarIcon.__init__(self)
        try:
            if "wxMSW" in wx.PlatformInfo:
                icon = ptk_icons.ptkicon16.GetIcon()
            elif "wxGTK" in wx.PlatformInfo:
                icon = ptk_icons.ptkicon22.GetIcon()
            elif "wxMac" in wx.PlatformInfo:
                icon = ptk_icons.ptkicon48.GetIcon()
        except:
            icon = ptk_icons.ptkicon16.GetIcon()
        
        self.tool = tool
        self.SetIcon(icon, 'PythonToolkit (PTK)')

        #bind some events
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.OnMenu)
        
        #create the menu
        self.menu = wx.Menu()   

        self.menu.Append(wx.ID_ABOUT, 'About...', 'About this program...') 
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)

        item = self.menu.Append(wx.ID_PREFERENCES, 'Preferences', 'Edit the program preferences')
        self.Bind(wx.EVT_MENU, self.OnPreferences, id=wx.ID_PREFERENCES)
        self.menu.AppendSeparator()

        #Tools add themselves here...

        self.menu.AppendSeparator()
        self.menu.Append(wx.ID_EXIT, 'Exit','Exit the application')
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)

    def OnMenu(self,event):
        """Open the menu"""
        self.PopupMenu(self.menu)

    def OnAbout(self, event):
        """Open the about dialog"""
        PTKInfoDialog()

    def OnPreferences(self,event):
        """Open the preferences dialog"""
        self.tool.show_settings()

    def OnLeftDClick(self,event):
        """Open the console"""
        app = wx.GetApp()
        console = app.toolmgr.get_tool('Console')
        console.show_console()
        
    def OnExit(self,event):
        """Exit the application"""
        wx.GetApp().Exit()

#---Info dialog-----------------------------------------------------------------
def PTKInfoDialog():
    """Open the ptk info dialog"""

    descrip = """An interactive environment for Python."""

    licence = """Copyright (c) 2009 T.Charrett

Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the "Software"), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of 
the Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS 
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """
    global VERSION

    info = wx.AboutDialogInfo()
    info.SetIcon( ptk_icons.about.GetIcon())
    #info.SetIcon( ptk_icons.ptkicon48.GetIcon())
    info.SetName('PythonToolkit (PTK)')
    info.SetVersion(VERSION)
    info.SetDescription(descrip)
    info.SetCopyright('(C) 2009 T Charrett')
    info.SetWebSite('http://pythontoolkit.sourceforge.net')
    info.SetLicence(licence)
    info.AddDeveloper('Tom Charrett')
    wx.AboutBox(info)


