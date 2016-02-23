import os.path
import wx
from ptk_lib.resources import common16
from ptk_lib.controls import WWStaticText
from ptk_lib.controls import dialogs

from ptk_lib.core_tools.fileio import DoFileDialog

#---Engine choice dialog--------------------------------------------------------
class EngineChoiceDialog(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__(self,None,-1,title,
                            style=wx.DEFAULT_DIALOG_STYLE,size=(400,300))

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #engine label box
        namebox = wx.StaticBox(self, -1, "Engine label:")
        boldfont = namebox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        namebox.SetFont(boldfont)
        namesizer = wx.StaticBoxSizer(namebox, wx.VERTICAL)
        self.name = wx.TextCtrl(self, -1, 'New engine', size=(125, -1))
        namesizer.Add(self.name,0,wx.EXPAND|wx.ALL,5)
        sizer.Add(namesizer,0,wx.EXPAND|wx.ALL,5)

        #engine type drop list
        app = wx.GetApp()
        tool = app.toolmgr.get_tool('Console')
        self.engdesc = tool.get_engine_descriptions()
        self.engtypes = tool.get_engine_types()

        #remove the internal option if it is already started
        if tool.internal is not None:
            self.engtypes.pop( self.engtypes.index('Internal') )

        typebox = wx.StaticBox(self, -1, "Engine type:")
        typebox.SetFont(boldfont)
        typesizer = wx.StaticBoxSizer(typebox, wx.VERTICAL)

        self.typech = wx.Choice(self, -1, (100, 50), choices = self.engtypes)
        self.Bind(wx.EVT_CHOICE, self.OnEngType, self.typech)
        typesizer.Add(self.typech,0,wx.EXPAND|wx.ALL,5)

        self.descrip = WWStaticText(self, -1, self.engdesc['Internal'])
        typesizer.Add(self.descrip,1,wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL,5)

        sizer.Add(typesizer,1,wx.EXPAND|wx.ALL,5)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)

        ok = wx.Button(self, wx.ID_OK, "OK")
        self.Bind(wx.EVT_BUTTON,self.OnOK,ok)
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add( ok,0,wx.ALIGN_RIGHT|wx.ALL,5)
        hsizer.Add( cancel,0,wx.ALIGN_RIGHT|wx.ALL,5)
        sizer.Add(hsizer,0,wx.ALIGN_RIGHT)

        #remember the last selection
        config = app.GetConfig()
        config.SetPath("Console//")
        last_eng = config.Read("last_engine_used",'wxEngine')
        if last_eng not in self.engtypes:
            last_eng='wxEngine'
        n = self.engtypes.index(last_eng)
        self.typech.SetSelection(n)
        self.OnEngType(None) #check the name field/description

    def OnEngType(self,event):
        """Update the engine description when the engine type is changed"""
        n=self.typech.GetSelection()
        engtype=str(self.engtypes[n]) 
        #check the name for internal engines
        if engtype=='Internal': #internal engine can only be called internal
            self.name.SetValue('Internal')
            self.name.Disable()
        else:
            self.name.Enable()
            self.name.SetValue('New engine')
        #update the engine description
        self.descrip.SetLabel( self.engdesc[engtype])

    def OnOK(self,event):
        """Store the selected engine type"""
        engname,engtype = self.GetValue() 
        if engtype is not 'Internal':
            #store the selection
            n=self.typech.GetSelection()
            app=wx.GetApp()
            config = app.GetConfig()
            config.SetPath("Console//")
            last_eng = config.Write("last_engine_used",self.engtypes[n])
        event.Skip()

    def GetValue(self):
        """Returns the engine label and selected type"""
        n=self.typech.GetSelection()
        engtype=str(self.engtypes[n])
        name=self.name.GetValue()
        return name,engtype


#---Run dialog------------------------------------------------------------------
class RunNewEngineDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self,None,-1, 'Run file in new engine',
                            style=wx.DEFAULT_DIALOG_STYLE,size=(400,300))

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #file path box
        namebox = wx.StaticBox(self, -1, "Filename:")
        boldfont = namebox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        namebox.SetFont(boldfont)

        namesizer = wx.StaticBoxSizer(namebox, wx.HORIZONTAL)
        self.file = wx.TextCtrl(self, -1, '')
        self.setfile = wx.BitmapButton( self, -1, common16.document_open.GetBitmap())
        self.setfile.SetToolTipString('Select file') 
        self.Bind(wx.EVT_BUTTON, self.OnSetFile, self.setfile)

        namesizer.Add(self.file, 1, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        namesizer.Add(self.setfile, 0, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(namesizer,0,wx.EXPAND|wx.ALL,5)

        #engine types for drop list
        app = wx.GetApp()
        tool = app.toolmgr.get_tool('Console')
        self.engdesc = tool.get_engine_descriptions()
        self.engtypes = tool.get_engine_types()

        #remove the internal engine option!
        self.engtypes.remove('Internal')
        self.engdesc.pop('Internal')

        #engine type box
        typebox = wx.StaticBox(self, -1, "Engine type:")
        typebox.SetFont(boldfont)
        typesizer = wx.StaticBoxSizer(typebox, wx.VERTICAL)

        self.typech = wx.Choice(self, -1, (100, 50), choices = self.engtypes)
        self.Bind(wx.EVT_CHOICE, self.OnEngType, self.typech)
        typesizer.Add(self.typech,0,wx.EXPAND|wx.ALL,5)

        self.descrip = WWStaticText(self, -1, '')
        typesizer.Add(self.descrip,1,wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL,5)

        sizer.Add(typesizer,1,wx.EXPAND|wx.ALL,5)

        #remember the last selection
        config = app.GetConfig()
        config.SetPath("Console//")
        last_eng = config.Read("last_engine_used",'wxEngine')
        if last_eng not in self.engtypes:
            last_eng='wxEngine'
        n = self.engtypes.index(last_eng)
        self.typech.SetSelection(n)
        self.OnEngType(None) #check the name field/description

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)

        ok = wx.Button(self, wx.ID_OK, "OK")
        self.Bind(wx.EVT_BUTTON,self.OnOK,ok)
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add( ok,0,wx.ALIGN_RIGHT|wx.ALL,5)
        hsizer.Add( cancel,0,wx.ALIGN_RIGHT|wx.ALL,5)
        sizer.Add(hsizer,0,wx.ALIGN_RIGHT)

    def OnSetFile(self, event):
        """Set the filepath"""
        paths, index = DoFileDialog(self, message="Choose a file",
            defaultFile="",
            wildcard='Python scripts|*.py;*.pyw|All files|*.*;*',
            style=wx.OPEN | wx.CHANGE_DIR,
            engname = None)
        if paths is None:
            return
        self.file.SetValue(paths[0])

    def OnEngType(self,event):
        """Update the engine description when the engine type is changed"""
        n=self.typech.GetSelection()
        engtype=str(self.engtypes[n]) 
        #update the engine description
        self.descrip.SetLabel( self.engdesc[engtype])

    def OnOK(self,event):
        """Store the selected engine type"""
        #store the selection
        n=self.typech.GetSelection()
        app=wx.GetApp()
        config = app.GetConfig()
        config.SetPath("Console//")
        last_eng = config.Write("last_engine_used",self.engtypes[n])
        event.Skip()

    def GetValue(self):
        """Returns the file and selected engine type"""
        n=self.typech.GetSelection()
        engtype=str(self.engtypes[n])
        filepath=self.file.GetValue()
        return filepath,engtype
        
    def SetFilepath(self, filepath):
        """Sets the filepath"""
        filepath = os.path.abspath(filepath)
        self.file.SetValue(filepath)
        

#---Dialog to manage command and arguments--------------------------------------
# Dialog to select file/cmd and add program arguments - also used for edit cmd.
class RunExternalDialog(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__(self,None,-1,title,
                            style=wx.DEFAULT_DIALOG_STYLE,size=(400,300))

        #create sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        #file path box
        namebox = wx.StaticBox(self, -1, "Filename:")
        boldfont = namebox.GetFont()
        boldfont.SetWeight(wx.BOLD)
        namebox.SetFont(boldfont)

        namesizer = wx.StaticBoxSizer(namebox, wx.VERTICAL)
        self.file = wx.TextCtrl(self, -1, '')
        self.setfile = wx.BitmapButton( self, -1, common16.document_open.GetBitmap())
        self.setfile.SetToolTipString('Select file to execute') 
        self.Bind(wx.EVT_BUTTON, self.OnSetFile, self.setfile)
        descrip = WWStaticText(self, -1, 'Executed using python -u FILEPATH ARGS')
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.file, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        hsizer.Add(self.setfile, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        namesizer.Add(hsizer,0, wx.EXPAND|wx.ALL,5)
        namesizer.Add(descrip,0, wx.EXPAND|wx.ALL,5)
        sizer.Add(namesizer,0,wx.EXPAND|wx.ALL,5)

        #args box
        argsbox = wx.StaticBox(self, -1, "Arguments:")
        argsbox.SetFont(boldfont)
        argssizer = wx.StaticBoxSizer(argsbox, wx.VERTICAL)

        #add a list box of arguments
        self.args = wx.ListBox( self,-1, choices=[], 
                                style=wx.LB_SINGLE|wx.HSCROLL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.args,1,wx.EXPAND, 0)

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
        argssizer.Add(hsizer, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add( argssizer, 1, wx.EXPAND|wx.ALL,5)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)

        ok = wx.Button(self, wx.ID_OK, "OK")
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add( ok,0,wx.ALIGN_RIGHT|wx.ALL,5)
        hsizer.Add( cancel,0,wx.ALIGN_RIGHT|wx.ALL,5)
        sizer.Add(hsizer,0,wx.ALIGN_RIGHT)

    #---------------------------------------------------------------------------
    def OnSetFile(self, event):
        """Set the filepath"""
        paths, index = DoFileDialog(self, message="Choose a file",
            defaultFile="",
            wildcard='Python scripts|*.py;*.pyw|All files|*.*;*',
            style=wx.OPEN | wx.CHANGE_DIR,
            engname = None)
        if paths is None:
            return
        self.file.SetValue(paths[0])

    def OnAdd(self, event):
        #add argument

        #show entry dialog
        d = wx.TextEntryDialog(None, 'New argument:','Enter script argument:')
        res = d.ShowModal()
        if res != wx.ID_OK:
            return

        #add to list control
        args = self.args.GetItems()
        args.append( d.GetValue() )
        self.args.SetItems( args )

    def OnRemove(self, event):
        #remove argument
        #first get the selection
        n = self.args.GetSelection()
        if n==-1:
            return

        #confirm
        msg='Delete selected argument?'
        title='Confirm argument removal'
        ans=dialogs.ConfirmDialog(msg,title)
        if ans is False:
            return
        #update the list
        args = self.args.GetItems()
        args.pop( n )
        self.args.SetItems(args)

    def OnMoveUp(self, event):
        #move argument up
        n = self.args.GetSelection()
        if n==-1:
            return
        args = self.args.GetItems()
        arg = args.pop(n)
        args.insert(n-1, arg)
        self.args.SetItems(args)
        self.args.SetSelection(n-1)

    def OnMoveDown(self, event):
        #move argument down
        n = self.args.GetSelection()
        if n==-1:
            return
        args = self.args.GetItems()
        arg = args.pop(n)
        args.insert(n+1, arg)
        self.args.SetItems(args)
        self.args.SetSelection(n+1)


    #---------------------------------------------------------------------------
    def GetValue(self):
        """Returns the filepath and arguments"""
        filepath = self.file.GetValue()
        args = self.args.GetItems()
        return filepath,args
        
    def SetValue(self, filepath, args):
        """Sets the filepath and arguments"""
        filepath = os.path.abspath(filepath)
        self.file.SetValue(filepath)
        self.args.SetItems(args)

