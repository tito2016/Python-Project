"""
This contains the editor notebook control. This handles and displays of the open
files in a tabbed notebook view.

EditorNotebook - the editor notebook class
"""
from subprocess import Popen, PIPE  #until Launcher/ExtEngine/wxProcess implemented
import os                           #for filepath functions
import textwrap                     #for text utils/removing common indent

import wx                           #for gui elements
import wx.aui                       #fancy notebook control
import wx.stc
from ptk_lib.core_tools.fileio import FileDrop,DoFileDialog
from ptk_lib.core_tools.console import console_dialogs

from editor_page import EditorPage

#---Editor notebook-------------------------------------------------------------
class EditorNotebook(wx.aui.AuiNotebook):   
    def __init__(self,parent):
        style = wx.aui.AUI_NB_DEFAULT_STYLE |wx.aui.AUI_NB_WINDOWLIST_BUTTON
        wx.aui.AuiNotebook.__init__(self,parent,-1,style=style)

        #create a droptarget
        self.dt = FileDrop(self.OpenFile)
        self.SetDropTarget(self.dt)  

        #internal to clear the paused markers from the correct filename
        # TODO: is there a better way - clear all pages?        
        self._lastpause = None

        #event bindings
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnClosePage)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnChangedPage)

        #self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

    #---Interface methods------------------------------------------------------- 
    # These are really just wrapper methods for the page methods
    #---------------------------------------------------------------------------
    def New(self):
        """Create a new empty page in the notebook"""
        page = EditorPage(self,-1)
        page.SetSavePoint() #set unchanged state
        #add to the notebook
        num = self.GetPageCount()
        name = 'unnamed ' + str(num)

        #add to the notebook
        self.AddPage(page,name)
        self.SetSelection(num) #set new page active
        #set focus if the only page as no page changed event!
        if self.GetPageCount() ==1:
            page.SetFocus()
    
        #savepoint events to mark the tabs as modified.
        self.Bind(wx.stc.EVT_STC_SAVEPOINTLEFT, self.OnPageSavePoint, page)
        self.Bind(wx.stc.EVT_STC_SAVEPOINTREACHED, self.OnPageSavePoint, page)

    def Open(self):
        """ method for menu/toolbar open dialog"""
        #Create the file open dialog.
        paths,index = DoFileDialog(self.Parent, wildcard = "Python source (*.py,*.pyw)|*.py;*.pyw|All files (*,*.*)|*.*;*")
        #Next open each file specified, load the data and create the pages
        if paths is None:
            return
        for path in paths:
            self.OpenFile(path)
        #ensure the parent frame is shown and raised to the top
        self.Parent.Show()
        self.Parent.Raise()

    def OpenFile(self,path):
        """ Opens a file sepcified by the path """
        path = os.path.abspath(path)
        path = os.path.normcase(path)
        #check file exists
        if os.path.exists(path) is False:
            return

        #check file path against open tabs
        page = self.GetPageFromPath(path)
        if page is not None:
            #show the already open file
            n = self.GetPageIndex(page)
            self.SetSelection(n)
            return

        #not already open so open in a new page and add to the notebook
        page = EditorPage(self,-1)
        page.LoadFile(path)
        name=os.path.basename(path)
        num = self.GetPageCount()
        self.AddPage(page,name)
        self.SetSelection(num) #set new page active
        
        #set focus if the only page as no page changed event!
        if self.GetPageCount() ==1:
            page.SetFocus()
            
        #savepoint events to mark the tabs as modified.
        self.Bind(wx.stc.EVT_STC_SAVEPOINTLEFT, self.OnPageSavePoint, page)
        self.Bind(wx.stc.EVT_STC_SAVEPOINTREACHED, self.OnPageSavePoint, page)

        #add to parents file history    
        self.Parent.filehistory.AddFileToHistory(path)

    def Save(self,num=None):
        """Save the current page, or the page number if given """
        if num is None:
            num  = self.GetSelection()  
            if num==-1: #no page
                return False
        page = self.GetPage(num)
        #check if previously saved
        if page._filename is '':
            #not saved before, do a saveas
            return self.SaveAs(num)
        else:
            return page.SaveFile(page._filename)

    def SaveAs(self, num=None):
        """
        Save the current page with a new filename, or the page number if given
        """
        if num is None:
            num  = self.GetSelection()
            if num==-1: #no page
                return False
        page = self.GetPage(num)

        #save as dialog
        dlg = wx.FileDialog(
                self, message="Save as:",
                defaultDir=os.getcwd(),
                defaultFile="",
                wildcard = "Python source (*.py)|*.py|Python source no command shell (*.pyw)|*.pyw|All files (*.*)|*.*",
                style= wx.SAVE | wx.OVERWRITE_PROMPT
                )
        #only save if not cancelled.
        if dlg.ShowModal() != wx.ID_OK:
            return False

        #get the enetered file path
        path = dlg.GetPath()

        #check extension specified use the dialog filters
        root,ext= os.path.splitext(path)
        if ext=='':
            type=dlg.GetFilterIndex()
            if type==0:
                ext = '.py'
            elif type==1:
                ext = '.pyw'
            else:
                ext = ''
        path = root+ext
        path = os.path.abspath(path)
        path = os.path.normcase(path)

        #save the file
        res = page.SaveFile(path)

        #add to parents file history    
        self.Parent.filehistory.AddFileToHistory(path)

        return res
    
    def Cut(self):
        """Cut from the current page"""
        num  = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Cut()

    def Copy(self):
        """Copy from the current page"""
        num  = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Copy()

    def Paste(self):
        """Paste from the current page"""
        num  = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Paste()

    def Undo(self):
        """Undo in the current page"""
        num  = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Undo()

    def Redo(self):
        """Redo in the current page"""
        num  = self.GetSelection()
        if num==-1: #no page
               return
        page = self.GetPage(num)
        page.Redo()

    def Indent(self):
        """Indent in the current page"""
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Indent()

    def Undent(self):
        """Undent in the current page"""
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Undent()

    def Comment(self):
        """Comment in the current page"""
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.Comment()

    def UnComment(self):
        """UnComment in the current page"""
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.UnComment()

    def InsertCellSeparator(self):
        """Insert a code cell separator"""
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        page.InsertCellSeparator()

    def Find(self,stext,back=False,flags=0):
        """
        Find the string in the current page.
        Returns true if found, false otherwise
        """
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        if back is True:
            found = page.FindPrevious(stext,flags)
        else:
            found = page.FindNext(stext,flags)
        return found
    
    def Replace(self,stext,rtext,back=False,flags=0):
        """
        Replace the selection (or find the next occurance if none selected)
        Returns true if found/replaced
        """
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        #see if there is a selection
        sel = page.GetSelectedText()
        #stext found previously replace it
        if sel==stext:
            page.ReplaceSelection(rtext)
            #find the next one
            found = self.Find(stext,back,flags)
        else:
            #not found yet do find next
            found = self.Find(stext,back,flags)

    def ReplaceAll(self,stext,rtext,back=False,flags=0):
        """
        Replace all in the direction specified
        """
        num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)
        #start with current selection
        sel = page.GetSelectedText()
        if sel==stext:
            page.ReplaceSelection(rtext)
            #find the next one
            found = self.Find(stext,back,flags)
        else:
            #not found yet do find next
            found = self.Find(stext,back,flags)

        #keep going until no more found
        while found is True:
            #see if there is a selection
            sel = page.GetSelectedText()
            if sel==stext:
                page.ReplaceSelection(rtext)
            #find the next one
            found = self.Find(stext,back,flags)
        return found

    #---Python page actions-----------------------------------------------------
    def Run(self, num=None):
        """
        Run the selected code or current cell in the page given by num in the 
        current engine as if entered at the console. 
        If num is None use the current page.
        """
        if num is None:
            num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)

        #check if there is any selection
        cmd  = page.GetSelectedText()
        if len(cmd)==0:
            #check for a cell
            cmd = page.GetCurrentCell()
            if cmd is None:
                dlg = wx.MessageDialog(self, "No selection or code cell, run entire file?", "Run",
                        wx.YES_NO | wx.YES_DEFAULT | wx.CANCEL | wx.ICON_QUESTION)
                result=dlg.ShowModal()
                dlg.Destroy()
                if result==wx.ID_YES:
                    self.ExecFile(num)
                return

        #remove any common indentation
        cmd = textwrap.dedent(cmd)
        
        #run the selected code in a PTK console if one exists
        console = wx.GetApp().toolmgr.get_tool('Console')
        eng = console.get_current_engine()
        if eng is not None:
            eng.exec_source(cmd)
            console.show_console()

    def ExecFile(self, num=None):
        """
        Execute the file given by page num in the current engine using execfile 
        command. If num is None use the current page.
        """
        if num is None:
            num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)

        #check if modified after last save
        if page.GetModify() is True:
            
            dlg = wx.MessageDialog(self, "Save changes?", "Editor",
                    wx.YES_NO | wx.YES_DEFAULT | wx.CANCEL | wx.ICON_QUESTION)
            result=dlg.ShowModal()
            dlg.Destroy()

            #actions depending upon answer
            if result==wx.ID_YES: #if yes try to save
                self.Save(num)
            elif result==wx.ID_CANCEL: #if cancel veto the execution
                return 

        #run the code in a PTK console if one exists
        console = wx.GetApp().toolmgr.get_tool('Console')
        console.exec_file(page._filename, engname=None)

    def ExtRun(self, num=None):
        """
        Run the file as an external process with a new console. If num is None 
        use the current page.
        """
        if num is None:
            num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)

        #run as external process
        abspath = page._filename
        if abspath is None:
            #not saved yet
            res = self.SaveAs(num) 
            if res is False:
                return
            abspath = page._filename

        #show the options dialog here
        d = console_dialogs.RunExternalDialog(self.Parent, 'Run script as external process')
        d.SetValue(abspath, [])
        res = d.ShowModal()
        if res==wx.ID_OK:
            filepath,args = d.GetValue()
            app = wx.GetApp()
            contool = app.toolmgr.get_tool('Console')
            contool.run_script( filepath, args)
            contool.show_console()
        d.Destroy()
        
    
    def RunNewEngine(self, num=None):
        """
        Run the file in the new engine. If num is None use the current page.
        """
        if num is None:
            num = self.GetSelection()
        if num==-1: #no page
            return
        page = self.GetPage(num)

        abspath = page._filename
        if abspath is None:
            #not saved yet
            res = self.SaveAs(num) 
            if res is False:
                return
            abspath = page._filename
        
        #Run in new engine
        d = console_dialogs.RunNewEngineDialog(self.Parent)
        d.SetFilepath(abspath)
        res=d.ShowModal()
        if res==wx.ID_OK:
            app = wx.GetApp()
            contool = app.toolmgr.get_tool('Console')
            filepath,engtype = d.GetValue()
            label = os.path.basename(filepath)
            contool.start_engine( engtype, label , filepath )
            contool.show_console()
        d.Destroy()
       
    def CloseAll(self):
        """Attempts to close all open pages - asks to save if necessary"""
        #loop over open tabs
        numpages = self.GetPageCount()
        for n in range(0,numpages):
            self.SetSelection(0)
            res = self.CheckPageClose(0)
            if res is False:
                return False
            page = self.GetPage(0)
            res = self.RemovePage(0)
            page.Destroy()
        return True
    
    def GetPageFromPath(self, path):
        """Get the editor page that contains the path, None if not opened"""
        path = os.path.abspath(path)
        path = os.path.normcase(path)

        #check each page
        numpages = self.GetPageCount()
        for n in range(0,numpages):
            page = self.GetPage(n)
            if page._filename == path:
                return page
        return None

    def GetAllPages(self):
        """
        Get all editor pages
        """
        pages = []
        numpages = self.GetPageCount()
        for n in range(0,numpages):
            pages.append( self.GetPage(n) )
        return pages

    def GetCurrentPage(self):
        """
        Get the current editor page
        """
        n = self.GetSelection()
        if n is -1:
            return None
        page = self.GetPage(n)
        return page

    #---Debugger methods--------------------------------------------------------
    def UpdatePauseMarkers(self):
        """
        Update any paused indicator symbols in the editor pages.
        For example if the current engine has switched, paused or resumed.
        """
        console = wx.GetApp().toolmgr.get_tool('Console')
        eng = console.get_current_engine()

        if self._lastpause is not None:
            #clear any existing paused marker
            self._lastpause.MarkerDeleteAll(1)
            self._lastpause = None

        if eng is None:
            #no engine - nothing else to do
            return

        #engine is not paused - nothing else to do
        if eng.debugger.filename is None:
            return

        #paused - get the filename and page
        filename = os.path.abspath(eng.debugger.filename)
        filename = os.path.normcase(filename)
        page =   self.GetPageFromPath( filename )     
        if page is not None:
            self._lastpause = page
            #add new marker
            hnd = page.MarkerAdd(eng.debugger.lineno-1, 1)

    #---events------------------------------------------------------------------
    def OnPageSavePoint(self, event):
        #page has left/reached a save point mark 'dirty'/clean
        num = self.GetSelection()
        if num==-1:
            return
        self.CheckTabName(num)
        event.Skip()

    def OnClosePage(self,event):
        """This method is called when a tab is closed"""
        num  = self.GetSelection()  
        page = self.GetPage(num)
        result = self.CheckPageClose(num)
        if result is False:
            event.Veto()
        else:
            event.Skip()

    def OnChangedPage(self,event):
        num  = self.GetSelection()  
        if num!=-1:
            page = self.GetPage(num)
            page.SetFocus()
  
    #---Checking methods--------------------------------------------------------
    def CheckClose(self):
        """check if open tabs are saved - return true if ok to close"""
        #loop over open tabs
        numpages = self.GetPageCount()
        for page in range(0,numpages):
            ans  = self.CheckPageClose(page)
            #return false if a page doesn't want to close
            if ans is False:
                return False
        return True

    def CheckPageClose(self,num):
        """Check if it is ok to close a page"""
        page = self.GetPage(num)
        if page.GetModify() is True:
            #ask if save/discard or cancel close
            abspath = page._filename
            if abspath is '':
                name = self.GetPageText(num)
                if name[-1]=='*':
                    name=name[0:-2]
                msg = "Save file? "+name
            else:
                name=os.path.basename(abspath)
                msg = "Save changes to: "+name+" ?"

            dlg = wx.MessageDialog(self, msg, "Editor",
                    wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_QUESTION)
            result=dlg.ShowModal()
            dlg.Destroy()

            #actions depending upon answer
            if result==wx.ID_YES: #if yes try to save
                self.Save(num)
                return True
            elif result==wx.ID_CANCEL: #if cancel veto the close
                return False
            elif result==wx.ID_NO:
                return True
        return True

    def CheckTabName(self,num):
        """Updates the tabname"""
        page = self.GetPage(num)
        if page._filename == '':
            #unsaved get current name
            name = self.GetPageText(num)
            if name[-1]=='*':
               name=name[0:-2]
        else:
            #saved 
            name=os.path.basename(page._filename)

        #check modification state
        if page.GetModify()==True:
            name = name+' *'
        self.SetPageText(num,name)
    
