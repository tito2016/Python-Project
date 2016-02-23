"""
PathManager controls
"""

#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---Imports---------------------------------------------------------------------
import os
import wx

from ptk_lib.resources import common16
from ptk_lib.controls import aui_addons
from ptk_lib.controls import toolpanel
from ptk_lib.controls import dialogs

from ptk_lib.core_tools.console import console_messages

import pathman_icons                          
import pathman_tasks                               


#---the pathlist control for the toolbar----------------------------------------
class PathList(wx.ComboBox):
    """The current working directory selection toolbar item"""
    def __init__(self,parent, tool):
        """Create the pathlist control - provides a drop list of paths"""

        #get a reference to the Console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #pathmanager tool
        self.tool = tool

        #create combobox
        wx.ComboBox.__init__(self, parent, -1, "", choices=[],
                                size=(300,-1), style=wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)
        
        #bind events
        self.Bind(wx.EVT_COMBOBOX, self.OnChange, self)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnText, self)

        #current path
        self.cur = ''

        #subcribe to these subjects
        self.tool.msg_node.subscribe(console_messages.CONSOLE_SWITCHED,
                                        self.msg_con_switched)

    def LoadPaths(self):
        """Load previous paths from config"""
        cfg = wx.GetApp().GetConfig()

        #get the recent paths
        paths = [os.getcwd()]
        for n in range(0,10):
            if cfg.Exists("PathManager//recent"+str(n)) :
               path = cfg.Read("PathManager//recent"+str(n))
               if paths.count(path)==0 and os.path.isdir(path):
                    paths.append(path)
        self.SetItems(paths)
        self.cur = paths[0]
        self.SetSelection(0)

    def SavePaths(self):
        """Save the path list history to config"""
        cfg = wx.GetApp().GetConfig()
        #save the current working directory paths
        paths = self.GetItems()
        #cut down to 10 only
        paths = paths[:10]
        n=0
        for path in paths: 
            cfg.Write("PathManager//recent"+str(n), path)
            n=n+1
        cfg.Flush() 

    def OnChange(self,event):
        new = event.GetString()
        result = self.ChangeDir(new)

    def OnText(self,event):
        new = event.GetString()
        self.ChangeDir(new)

    def ChangeDir(self,path):
        #change the current engines path
        eng=self.console.get_current_engine()
        if eng is not None:
            ok = eng.run_task('set_cwd',(path,))
        else:
            ok = True

        if ok is True:
            #update the control
            self.SetControlPath(path)

            #update ptk working directory
            os.chdir(path)

            #publish message
            self.tool.msg_node.publish_msg('PathManager.CWDChanged',(path,))

        else:
            #restore to previous
            self.SetString(self.GetSelection(),self.cur)

    def SetControlPath(self,path):
        """Set the list to display the path"""
        #check if this dir is in the list
        self.cur = path
        items = self.GetItems()
        if items.count(path)>0:
            #it is so remove it
            n = items.index(path)
            item = items.pop(n)
        #not in list, insert at 0
        items.insert(0,path)
        self.SetItems(items)
        self.SetSelection(0)

    def CheckControlPath(self):
        """Check the control is showing the right path"""
        eng=self.console.get_current_engine()
        if eng is not None:
            cwd_engine = eng.run_task('get_cwd')
        else:
            cwd_engine = os.getcwd()

        #check control's display
        if cwd_engine!=self.cur:
            self.SetControlPath(cwd_engine)

    #---Message handlers--------------------------------------------------------
    def msg_con_switched(self,msg):
        """
        Message handler for CONSOLE_SWITCHED message - these are emitted when 
        the active console is changed, here we check the current working 
        directory is ok.
        """
        eng = self.console.get_current_engine()
        if eng is None:
            return
        ok = eng.run_task('set_cwd', (self.cur,))
        if ok is False:
            log.error('Error setting engine cwd for path: '+str(self.cur))

#---The Pathmanager toolbar-----------------------------------------------------
class PathManTools(toolpanel.ToolPanel):
    def __init__(self,parent, tool):

        toolpanel.ToolPanel.__init__(self,parent,-1)

        self.tool = tool
 
        #get a reference to the Console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')
       
        #set the status bar to use
        self.SetStatusBar(self.console.frame.StatusBar)

        #set the icon size
        self.SetToolBitmapSize((16,16))

        #load some icons
        bmp_browse  = common16.folder.GetBitmap() 
        bmp_manager   = pathman_icons.pathmanager16.GetBitmap()

        #Current path list
        self.AddStaticLabel( 'Current directory: ')
        self.pathlist = PathList(self, tool)
        self.AddControl(self.pathlist)

        #browser
        self.browseid = wx.NewId()
        self.AddTool( self.browseid, bmp_browse, wx.ITEM_NORMAL,
                        'Browse for a directory',
                        'Browse for a directory')
        self.Bind(wx.EVT_TOOL, self.OnBrowse, id=self.browseid)

        #path dialog
        self.manid = wx.NewId()
        self.AddTool( self.manid, bmp_manager, wx.ITEM_NORMAL,
                            'Open the path manager',
                            'Open the path manager')
        self.Bind(wx.EVT_TOOL, self.OnShowManager, id=self.manid)

        self.Realize()
        
        #subscribe to engine switched messages
        self.tool.msg_node.subscribe(console_messages.CONSOLE_SWITCHED,
                                    self.msg_con_switched)

    #---messages----------------------------------------------------------------
    def msg_con_switched(self,msg):
        """CONSOLE_SWITCHED message handler"""
        eng = self.console.get_current_engine()
        #check for no active engine
        if eng is None:
            flag = False
        else:
            flag = True

        #enable/disable toolbar buttons
        self.EnableTool(self.manid , flag)

    #---events------------------------------------------------------------------
    def OnBrowse(self,event):
        """open a directory browser"""
        eng=self.console.get_current_engine()
        if eng is None:
            engcwd = os.getcwd()
        else:
            engcwd = eng.run_task('get_cwd')
        dir = wx.DirSelector(defaultPath=engcwd) #use the engines cwd
        if dir!='':
            self.pathlist.ChangeDir(dir)

    def OnShowManager(self,event):
        """open the path manager dialog"""
        #check if there is an engine
        eng=self.console.get_current_engine()
        if eng is None:
            return
        #show the dialog
        d=PathManDialog(None)
        d.ShowModal()

#---the dialog display to edit paths--------------------------------------------
class PathManDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=-1, title='Edit system paths', 
                            size=(400, 375),
                            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        #set the window icon
        icon = pathman_icons.pathmanager16.GetIcon()
        self.SetIcon(icon)

        panel = PathManPanel(self)
        line = wx.StaticLine(self)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, wx.ID_OK, 'Done')
        hbox.Add(okButton, 1,wx.TOP|wx.LEFT,5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(panel,1,wx.EXPAND|wx.ALL,5)
        vbox.Add(line,0,wx.EXPAND,0)
        vbox.Add(hbox, 0, wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM| wx.ALL, 5)

        self.SetSizer(vbox)
        self.SetMinSize((400,250))


#---The path manager panel------------------------------------------------------
class PathManPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,id=-1)

        #get a reference to the Console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #register enginetasks
        eng = self.console.get_current_engine()
        tasks =  eng.get_registered_tasks()
        if 'get_sys_path' not in tasks:
            eng.register_task(pathman_tasks.get_sys_path)
        if 'add_to_sys_path' not in tasks:
                eng.register_task(pathman_tasks.add_to_sys_path)
        if 'remove_from_sys_path' not in tasks:
                eng.register_task(pathman_tasks.remove_from_sys_path)
        if 'move_up_sys_path' not in tasks:
                eng.register_task(pathman_tasks.move_up_sys_path)
        if 'move_down_sys_path' not in tasks:
                eng.register_task(pathman_tasks.move_down_sys_path)

        #static box
        box = wx.StaticBox(self, -1, "Python module search path (sys.path):")
        boldfont = box.GetFont()
        boldfont.SetWeight(wx.BOLD)
        box.SetFont(boldfont)
        boxsizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        #add a list box of sys.path
        paths = eng.run_task( 'get_sys_path' )
        self.plist = wx.ListBox(self,-1, choices=paths, 
                    style=wx.LB_SINGLE|wx.HSCROLL)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.plist,1,wx.EXPAND, 0)

        #add remove/add buttons
        self.add    = wx.BitmapButton(self, -1, common16.add.GetBitmap())
        self.add.SetToolTipString('Add a new path') 
        self.Bind(wx.EVT_BUTTON, self.OnAdd, self.add)

        self.remove = wx.BitmapButton(self, -1, common16.remove.GetBitmap())
        self.remove.SetToolTipString('Remove path') 
        self.Bind(wx.EVT_BUTTON, self.OnRemove, self.remove)

        #add updown buttons
        self.up    = wx.BitmapButton(self, -1, common16.go_up.GetBitmap())
        self.up.SetToolTipString('Move path up in search order') 
        self.Bind(wx.EVT_BUTTON, self.OnMoveUp, self.up)

        self.down = wx.BitmapButton(self, -1, common16.go_down.GetBitmap())
        self.down.SetToolTipString('Move path down in search order') 
        self.Bind(wx.EVT_BUTTON, self.OnMoveDown, self.down)

        butsizer = wx.BoxSizer(wx.VERTICAL)
        butsizer.Add(self.add,1,wx.EXPAND|wx.LEFT|wx.RIGHT,2)
        butsizer.Add(self.remove,1,wx.EXPAND|wx.LEFT|wx.RIGHT,2)
        butsizer.Add(self.up,1,wx.EXPAND|wx.LEFT|wx.RIGHT,2)
        butsizer.Add(self.down,1,wx.EXPAND|wx.LEFT|wx.RIGHT,2)
        
        hsizer.Add(butsizer)
        boxsizer.Add(hsizer, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(boxsizer)

    
    def OnAdd(self,event):
        """Add a new path to the sys.path"""
        dirname = wx.DirSelector(defaultPath=os.getcwd())
        if dirname!='':
            eng = self.console.get_current_engine()
            #add the dir to the engines sys.path
            paths = eng.run_task('add_to_sys_path',(dirname,))
            #update the list
            self.plist.SetItems(paths)

    def OnRemove(self,event):
        """Removes the currently selected path from sys.path"""
        #first get the selection
        n = self.plist.GetSelection()
        if n==-1:
            return
        msg='Delete selected path from search paths?'
        title='Confirm path removal'
        ans=dialogs.ConfirmDialog(msg,title)
        if ans is True:
            dirname = self.plist.GetString(n)
            #remove the dir from the engines sys.path
            eng = self.console.get_current_engine()
            paths = eng.run_task('remove_from_sys_path',(dirname,))
            #update the list
            self.plist.SetItems(paths)

    def OnMoveUp(self,event):
        #first get the selection
        n = self.plist.GetSelection()
        if n==-1:
            return
        dirname = self.plist.GetString(n)
        #move the dir up in the engines sys.path
        eng = self.console.get_current_engine()
        paths,newn = eng.run_task('move_up_sys_path',(dirname,))
        #update the list
        self.plist.SetItems(paths)
        self.plist.SetSelection(newn)

    def OnMoveDown(self,event):
        #first get the selection
        n = self.plist.GetSelection()
        if n==-1:
            return
        dirname = self.plist.GetString(n)
        #move the dir down in the engines sys.path
        eng = self.console.get_current_engine()
        paths,newn = eng.run_task('move_down_sys_path',(dirname,))
        #update the list
        self.plist.SetItems(paths)
        self.plist.SetSelection(newn)
