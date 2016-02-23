"""
IO using the python pickle and shelve modules.


TODO:   Options and naming dialog.   
"""
import os.path
from fileio_dialogs import MultipleObjectToFileDialog
from fileio_misc import Exporter, Importer
import wx

class PickleImporter(Importer):
    def __init__(self):
        Importer.__init__( self,'Import data from Python pickle/shelve file formats',
                                ['.dat','.shelve'],
                                data=True,
                                wildcards = ['Python pickle file (.dat)|*.dat;',
                                             'Python shelve file (*.shelve)|*.shelve;'],
                                descrip= 'Import data previously saved using the Python pickle (single object per file) or shelve (multiple objects per file) modules'
                           )

    def __call__(self, filepath):
        root,ext = os.path.splitext(filepath)
        if ext =='.dat':
            self.import_pickle(filepath)
        elif ext=='.shelve':
            self.import_shelve(filepath)
        else:
            #create and show dialog
            dlg = wx.SingleChoiceDialog( None, 'Import using: ', 
                                     'Pickle import: Unknown file extension',
                                     ['pickle','shelve'], wx.CHOICEDLG_STYLE)
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            n = dlg.GetSelection()
            if n==0:
                self.import_pickle(filepath)
            else:
                self.import_shelve(filepath)

    def import_pickle(self,filepath):
        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_current_engine()
        #register import task with engine
        if 'pickle_import' not in engine.get_registered_tasks():
            engine.register_task(pickle_import)
        #import
        err = engine.run_task('pickle_import',(filepath,))
        #check return err
        if err!='':
            #show error message dialo
            d = ScrolledMessageDialog(None,err,"Import error")
            d.ShowModal()
            d.Destroy()

        #check return err
        if err!='':
            #show error message dialog
            d = ScrolledMessageDialog(None,err,"Export error")
            d.ShowModal()
            d.Destroy()

        #publish state change message to other tools
        engine.notify_change()

    def import_shelve(self,filepath):
        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_current_engine()
        #register import task with engine
        if 'shelve_import' not in engine.get_registered_tasks():
            engine.register_task(shelve_import)
        #import
        err = engine.run_task('shelve_import',(filepath,))
        #check return err
        if err!='':
            #show error message dialo
            d = ScrolledMessageDialog(None,err,"Import error")
            d.ShowModal()
            d.Destroy()
        
        #check return err
        if err!='':
            #show error message dialog
            d = ScrolledMessageDialog(None,err,"Export error")
            d.ShowModal()
            d.Destroy()

        #publish engine state change message
        engine.notify_change()

class PickleExporter(Exporter):
    def __init__(self):
        Exporter.__init__(self,name='Python pickle/shelve', 
                            type_strings=[-1],
                            descrip='Export using the Python pickle/shelve modules')

    def __call__(self, engname, onames):
        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_engine_console(engname)

        #open file dialog
        d=MultipleObjectToFileDialog(None,engname,onames,
                exts=['dat','shelve'],
                ext_descrips=['pickle (*.dat)', 'shelve (*.shelve)'],
                ext_multi=[True,False] )

        #show and check return code
        res = d.ShowModal()
        if res!=wx.ID_OK:
            d.Destroy()
            return

        #get filepaths and type
        fnames = d.GetFilepaths()
        n = d.GetExtIndex()
        d.Destroy()

        #pickle each object to a file
        if n==0:
            #register export task with engine
            if 'pickle_export' not in engine.get_registered_tasks():
                engine.register_task(pickle_export)
            #export
            failed = engine.run_task('pickle_export',(onames,fnames))
        
        #use single file shelve.
        elif n==1:
            #register export task with engine
            if 'pickle_shelve_export' not in engine.get_registered_tasks():
                engine.register_task(pickle_shelve_export)
            #export
            failed = engine.run_task('pickle_shelve_export',(onames,fnames[0]))

        if len(failed)!=0:
            msg = "Pickle export failed for the following objects:\n"
            for name in failed:
                msg = msg+'\t'+name+'\n'
            dlg = wx.MessageDialog(None, msg, "Export failed",wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()

#---Engine tasks----------------------------------------------------------------
def pickle_export(globals, locals, onames, fnames):
    """
    pickle export engine task:
        onames = list of names to export
        fnames = list of filenames
    """
    import pickle
    failed=[]
    for oname,fname in zip(onames,fnames):
        try:
            f = file(fname,'w')
            obj = eval( oname, globals, locals)
            pickle.dump(obj,f)
            f.close()
        except:
            failed.append( oname )
            f.close()
    return failed

def pickle_shelve_export(globals, locals, onames,fname):
    """
    shelve export engine task:
        onames = list of names to export
        fname = filename
    """
    import shelve
    #create the shelve file
    failed = []
    d = shelve.open(fname)
    for oname in onames:
        try:
            obj = eval( oname, globals, locals)
            d[oname] = obj
        except:
            failed.append( oname )
    d.close()
    return failed

def pickle_import(globals, locals, filepath):
    """
    Pickle import engine task
    """
    import pickle
    import sys
    import traceback
    err=''
    try:
        f = file(filepath)
        obj = pickle.load(f)
        locals['pickle_data']=obj
    except:
        t,v = sys.exc_info()[:2]
        l = traceback.format_exception(t, v, None)
        for s in l:
            err=err+s
        err = err +'\n'
    return err

def shelve_import(globals, locals, filepath):
    """
    Shelve import engine task
    """
    import shelve
    import sys
    import traceback
    err=''
    try:
        obj = shelve.open(filepath)
        locals['shelve_data']=obj
    except:
        t,v,tb = sys.exc_info()
        l = traceback.format_exception(t, v, None)
        for s in l:
            err=err+s
        err = err +'\n'
    return err
