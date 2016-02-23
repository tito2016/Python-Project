"""
Numpy array Exporter

TODO:
        Split into numpy binary file and numpy text file
        Add importer options (to memmap etc) and object naming
"""
import os.path
import wx
from wx.lib.dialogs import ScrolledMessageDialog

from ptk_lib.controls import ScrolledText

from ptk_lib.core_tools.fileio import MultipleObjectToFileDialog, Importer, Exporter

#---Importer ------------------------------------------------------------------
class NumpyImporter(Importer):
    def __init__(self):
        Importer.__init__( self,'Import data from Numpy array file formats',
                                ['.txt','.npy','.npz'],
                                data=True,
                                wildcards = ['Numpy binary file (.npy, .npz)|*.npy; *.npz;',
                                             'Numpy text file format (*.txt)|*.txt;'],
                                descrip= 'Import using the numpy array file formats (numpy binary (.npy) / numpy binary zip archive (.npz) / numpy text file format (.txt)'
                           )

    def __call__(self, filepath):
        root,ext = os.path.splitext(filepath)
        if ext in ['.npy','.npz']:
            self.import_load(filepath)
        elif ext=='.txt':
            self.import_loadtxt(filepath)
        else:
            #create and show dialog
            dlg = wx.SingleChoiceDialog( None, 'Import using: ', 
                                     'Numpy import: Unknown file extension',
                                     ['Numpy binary','text'], wx.CHOICEDLG_STYLE)
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            n = dlg.GetSelection()
            if n==0:
                self.import_load(filepath)
            else:
                self.import_loadtxt(filepath)

    def import_load(self,filepath):

        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_current_engine()

        #register import task with engine
        if 'numpy_load' not in engine.get_registered_tasks():
            engine.register_task(numpy_load)
        #import
        err = engine.run_task('numpy_load',(filepath,))
        #check return err
        if err!='':
            #show error message dialo
            d = ScrolledMessageDialog(None,err,"Numpy Import error")
            d.ShowModal()
            d.Destroy()
        
        #publish engine state change message
        engine.notify_change()

    def import_loadtxt(self,filepath):

        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_current_engine()

        #register import task with engine
        if 'numpy_loadtxt' not in engine.get_registered_tasks():
            engine.register_task(numpy_loadtxt)
        #import
        err = engine.run_task('numpy_loadtxt',(filepath,','))
        #check return err
        if err!='':
            #show error message dialo
            d = ScrolledMessageDialog(None,err,"Numpy Import error")
            d.ShowModal()
            d.Destroy()
        
        #publish engine state change message
        engine.notify_change()

    
#---Exporter -------------------------------------------------------------------
class NumpyExporter(Exporter):
    def __init__(self):
        Exporter.__init__(self,name='Numpy array file formats', 
                            type_strings=['numpy.ndarray','numpy.core.memmap.memmap'],
                            descrip='Export using the numpy array file formats (numpy binary (.npy) / numpy binary zip archive (.npz) / numpy text file format (.txt)'
                            )

    def __call__(self, engname, onames):
        #get engine
        console = self.app.toolmgr.get_tool('Console')
        engine = console.get_engine_console(engname)
        if (engine is None) or (engine.is_interactive is False):
            log.warning('Attempy to export from non-existant engine!')

        #open file dialog
        d=MultipleObjectToFileDialog(None,engname,onames,
                    exts=['npy','npz','txt'],
                    ext_descrips=['numpy binary (*.npy)','numpy binary zip (*.npz)', 'numpy text (*.txt)'],
                    ext_multi=[True,False,True] )
        #add options dialogs
        opt_txt = NumpyTxtOptionsDialog(d,fmt='%.18e', delimiter='')
        d.SetOptionsDialog('txt',opt_txt)

        #show and check return code
        res = d.ShowModal()
        if res!=wx.ID_OK:
            d.Destroy()
            return

        #get filepaths and type
        fnames = d.GetFilepaths()
        ext = d.GetExt()
        d.Destroy()
        opt_txt.Destroy()

        #numpy binary format
        if ext=='npy':
            #register export task with engine
            if 'numpy_save' not in engine.get_registered_tasks():
                engine.register_task(numpy_save)
            #export
            err = engine.run_task('numpy_save',(onames,fnames))

        #numpy binary zip format
        elif ext=='npz':
            #register export task with engine
            if 'numpy_savez' not in engine.get_registered_tasks():
                engine.register_task(numpy_savez)
            #export
            err = engine.run_task('numpy_savez',(onames,fnames[0]))

        elif ext=='txt':
            #get options from text options dialo
            fmt, delimiter = opt_txt.GetOptions()
            #register export task with engine
            if 'numpy_savetxt' not in engine.get_registered_tasks():
                engine.register_task(numpy_savetxt)
            #export
            err = engine.run_task('numpy_savetxt',(onames, fnames, fmt, delimiter))

        #check return err
        if err!='':
            #show error message dialog
            d = ScrolledMessageDialog(None,err,"Export error")
            d.ShowModal()
            d.Destroy()


#---Engine tasks----------------------------------------------------------------
def numpy_save(globals, locals, onames, fnames):
    """
    numpy save engine task:
        onames = list object names to export
        fnames = list of filenames
    """
    #import inside function to perform import in engine process
    import numpy
    import sys
    import traceback
    err = ''
    for fname,oname in zip(fnames,onames): 
        try:
            arr = eval(oname ,globals, locals)
            numpy.save(fname, arr)
        except:
            t,v = sys.exc_info()[:2]
            l = traceback.format_exception(t, v, None)
            for s in l:
                err=err+s
            err = err +'\n'
    return err

def numpy_savez(globals, locals, onames, fname):
    """
    numpy save engine task:
        fname = filename
        onames = list object names to export
    """
    #import inside function to perform import in engine process
    import numpy
    import sys
    import traceback
    #build kwargs dict for numpy.savez
    kwargs = {}
    err=''
    for oname in onames:
        try:
            arr = eval(oname ,globals, locals)
            kwargs[ oname ] = arr
        except:
            t,v = sys.exc_info()[:2]
            l = traceback.format_exception(t, v, None)
            for s in l:
                err=err+s
            err = err +'\n'

    #call numpy.savez
    try:
        numpy.savez( fname, **kwargs)
    except:
        err = err + error_handling.get_exception()
    return err

def numpy_savetxt(globals, locals, onames, fnames, fmt, delimiter):
    """
    numpy savetxt engine task:
        onames = object names to export
        fnames = filenames to export to.
        fmt    = format string (see numpy.savetxt)
        delimiter = delimiter string (see numpy.savetxt)
    """
    #import inside function to perform import in engine process
    import numpy
    import sys
    import traceback
    err = ''
    for fname,oname in zip(fnames,onames): 
        try:
            arr = eval(oname ,globals, locals)
            numpy.savetxt( fname, arr, fmt, delimiter)
        except:
            t,v = sys.exc_info()[:2]
            l = traceback.format_exception(t, v, None)
            for s in l:
                err=err+s
            err = err +'\n'
    return err

def numpy_load(globals, locals, fname):
    """
    numpy load engine task:
        fname = filename
    """
    import numpy
    import sys
    import traceback
    err=''
    try:
        arr = numpy.load(fname)
        locals['numpy_data']=arr
    except:
        t,v = sys.exc_info()[:2]
        l = traceback.format_exception(t, v, None)
        for s in l:
            err=err+s
        err = err +'\n'
    return err

def numpy_loadtxt(globals, locals, fname, delimiter):
    """
    numpy load engine task:
        fname = filename
        delimiter = delimiter string (see numpy.loadtxt)

    """
    import numpy
    import sys
    import traceback
    err=''
    try:
        arr = numpy.loadtxt(fname,delimiter=delimiter)
        locals['numpy_data']=arr
    except:
        t,v = sys.exc_info()[:2]
        l = traceback.format_exception(t, v, None)
        for s in l:
            err=err+s
        err = err +'\n'
    return err

#---options dialog--------------------------------------------------------------
class NumpyTxtOptionsDialog(wx.Dialog):
    def __init__(self,parent, fmt='%.18e', delimiter=','):
        """
        Numpy savetxt options dialog
        """
        wx.Dialog.__init__(self,parent,-1,title='Numpy savetxt options',
                            style=wx.DEFAULT_DIALOG_STYLE,
                            size=(360,150))
  
        sizer = wx.BoxSizer(wx.VERTICAL)

        panel=wx.Panel(self,-1)
        psizer=wx.BoxSizer(wx.VERTICAL)
        gsizer = wx.GridSizer(2,2)
        label = wx.StaticText(panel, -1, 'Format string', size=(150,-1))
        self.fmt = wx.TextCtrl(panel,-1,fmt)
        gsizer.Add(label,0,wx.ALL|wx.ALIGN_CENTER,5)
        gsizer.Add(self.fmt, 0,wx.ALL|wx.ALIGN_CENTER,5)
        
        label = wx.StaticText(panel, -1, 'Delimiter', size=(150,-1))
        self.delimiter = wx.TextCtrl(panel,-1,',')
        gsizer.Add(label,0,wx.ALL|wx.ALIGN_CENTER,5)
        gsizer.Add(self.delimiter, 0, wx.ALL|wx.ALIGN_CENTER,5)
        psizer.Add(gsizer, 0,wx.ALIGN_CENTER|wx.ALL,5)
        panel.SetSizer(psizer)

        sizer.Add(panel,1,wx.EXPAND)

        #create static line and OK/Cancel button
        line = wx.StaticLine(self,-1)
        sizer.Add(line,0,wx.EXPAND|wx.LEFT|wx.RIGHT,5)
        ok_but    = wx.Button(self, wx.ID_OK, "Done")
        sizer.Add(ok_but,0, wx.ALL|wx.ALIGN_RIGHT,5)

        self.SetSizer(sizer)

    def GetOptions(self):
        fmt = str(self.fmt.GetValue())
        dl = str(self.delimiter.GetValue())
        #allow tabs and newlines to be entered correctly
        dl = dl.replace('\\t','\t')
        dl = dl.replace('\\n','\n')
        dl = dl.replace('\\r','\r')
        return fmt, dl
    

