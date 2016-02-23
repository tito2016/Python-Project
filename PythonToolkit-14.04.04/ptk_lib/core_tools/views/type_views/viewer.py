"""
TypeViewer:
-------
The viewer class is a panel which will automatically check it objects type and
display the correct view inside itself. This means that if an object is deleted
or changes type the view will also update.

TypeView:
---------
A base class for gui views of a specific type.
 - View class should not use the engine interface once DisbleView is called 
   it may be closed and so no longer exist. 
 - The viewer automatically disbales views when the engine is closed.
 - View should publish an Engine.StateChange message after modifying an object
   to allow other tools to update.
"""
import wx

from ptk_lib.resources import common16

class TypeView(wx.Panel):
    """ 
    A panel class which displays object infomation this is a dummy which does 
    nothing.
    Arguments are parent/viewer, object name and engine.
    """
    def __init__(self,viewer,oname,eng):
        wx.Panel.__init__(self,viewer)
        self.oname = oname
        self.eng = eng
        self.viewer = viewer
        self.disabled = False

    def RefreshView(self):
        """
        This method is called by the Viewer pane to automatically update the 
        contents.
        """
        pass

    def DisableView(self):
        """Disable the view"""
        self.disabled = True
        self.Disable()

    def EnableView(self,eng):
        """Enable the view"""
        self.eng = eng
        self.disabled = False
        self.Enable()

#---Viewer class----------------------------------------------------------------
class TypeViewer(wx.Panel):
    def __init__(self,parent, tool, oname,engname):
        """Open a viewer pane for the object specified"""
        wx.Panel.__init__(self,parent)
        
        #parent tool
        self.viewtool = tool

        #get reference to the console tool
        app = wx.GetApp()
        self.console = app.toolmgr.get_tool('Console')

        #object details
        self.oname = oname    
        self.engname = engname
        
        #set up the sizer and message and contents panels
        self.psizer = wx.BoxSizer(wx.VERTICAL)

        #bmps for message bar
        self.bmps = {}
        self.bmps['info'] = common16.dialog_information.GetBitmap()
        self.bmps['error'] = common16.dialog_error.GetBitmap()
        self.bmps['warning'] = common16.dialog_warning.GetBitmap()

        #the message panel is a sizer containing an icon and static text
        self.msgpanel = wx.Panel(self,-1)
        self.msgpanel.SetMinSize((-1,20))
        self.msgpanel.SetMaxSize((-1,20))
        self.msgpanel.SetBackgroundColour(wx.RED)
        msgsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.msgbmp = wx.StaticBitmap(self.msgpanel,-1,self.bmps['error'])
        self.msgtext = wx.StaticText(self.msgpanel,-1,'')
        self.msgtext.Wrap(-1)
        msgsizer.Add(self.msgbmp,0,wx.ALL|wx.ALIGN_CENTER,10)
        msgsizer.Add(self.msgtext,1,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,10)
        self.msgpanel.SetSizer(msgsizer)
        self.psizer.Add(self.msgpanel,0,wx.EXPAND)
        
        #create dummy view and show message
        self.ShowMessage('No view for this object type',bmp='error')
        self.typestr=None
        self.view = TypeView(self,self.oname,self.engname)
        self.psizer.Add(self.view,1,wx.EXPAND)
        self.SetSizer(self.psizer)
        self.RefreshView()
    #---------------------------------------------------------------------------
    def ShowMessage(self,msg,bmp='error'):
        """Show the message panel and set the message text to msg"""
        self.msgtext.SetLabel(msg)
        self.msgbmp.SetBitmap(self.bmps[bmp])
        self.psizer.Show(0)
        self.psizer.Layout()

    def HideMessage(self):
        """Hide the message panel"""
        self.psizer.Hide(0)
        self.psizer.Layout()

    def RefreshView(self):
        """
        Refresh the view contents - this checks if the object exists and the 
        object type. If the object type has changed the current view panel is 
        Destroyed and a new view is created. Otherwise the current view is 
        Refreshed.
        """
        #get the engine
        eng = self.console.get_engine_console(self.engname)
        if (eng is None) or (eng.is_interactive is False):
            self.ShowMessage('The engine containing the object has been closed',bmp='error')
            self.view.DisableView()
            return

        #check object exists
        exists = eng.run_task('object_exists',(self.oname,))
        if exists is False:
            self.ShowMessage('The object no longer exists',bmp='error')
            self.view.DisableView()
            return

        #check the object type
        otype = eng.evaluate( self.oname+'.__class__.__module__ + "." +'+self.oname+'.__class__.__name__')

        #same as current view refresh it
        if otype==self.typestr:
            self.HideMessage()
            self.view.EnableView(eng)
            self.view.RefreshView()
            return

        #otherwise replace the view with one for the correct type
        #destroy old view
        self.psizer.Remove(self.view)
        self.view.Destroy()

        #get new viewer
        if self.viewtool.has_type_view(otype) is False:
            #create dummy view and show message
            self.ShowMessage('No view for this object type',bmp='error')
            self.typestr=None
            self.view = TypeView(self,self.oname,eng)
        else:
            view = self.viewtool.get_type_view(otype)
            #create the new view
            self.HideMessage()
            self.typestr=otype
            self.view = view(self,self.oname,eng)

        #refresh the sizer
        self.psizer.Add(self.view,1,wx.EXPAND)
        self.Layout()

    def Refresh(self):
        self.RefreshView()
        wx.Panel.Refresh(self)
