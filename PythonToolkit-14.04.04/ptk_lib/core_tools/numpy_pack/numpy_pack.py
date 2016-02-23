#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.INFO)

#---Imports---------------------------------------------------------------------
import os
import imp 

import wx
from ptk_lib.tool_manager import Tool

#extensions
from ptk_lib.core_tools.nsbrowser import type_icons

from numpy_io import NumpyImporter, NumpyExporter
import array_view

class NumPyPack(Tool):
    name = 'NumPy Pack'
    descrip = 'Tool providing NumPy extensions, including array importers, exporters, gui viewer and namespace browser extensions'  
    author = 'T.Charrett'
    requires = ['NSBrowser','FileIO']           
    core = True            
    icon = None

    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')

        try:
            imp.find_module('numpy')
        except:
            log.exception('error cannot find numpy: Is numpy installed?')
            raise Exception('error cannot find numpy: Is numpy installed?')

        app = wx.GetApp()

        #FileIO extensions
        fileio = app.toolmgr.get_tool('FileIO')
        self.exporter = NumpyExporter()
        fileio.register_exporter( self.exporter )
        self.importer = NumpyImporter()
        fileio.register_importer(self.importer)

        #NSBrowser icons
        nsb = app.toolmgr.get_tool('NSBrowser')
        nsb.set_type_icon('numpy.ufunc' , type_icons.fnc_icon.GetIcon())
        nsb.set_type_icon('numpy.ndarray' , type_icons.array_icon.GetIcon())
        nsb.set_type_icon('numpy.core.memmap.memmap' , type_icons.array_icon.GetIcon())   

        #NSBrowser infovalues
        nsb.set_type_info('numpy.ndarray', array_infovalue)
        nsb.set_type_info('numpy.core.memmap.memmap', array_infovalue)

        #Object views
        views = app.toolmgr.get_tool('Views')
        views.set_type_view('numpy.ndarray',array_view.ArrayView)
        views.set_type_view('numpy.core.memmap.memmap',array_view.ArrayView)

        log.info('Done Initialising tool')


#---NSBrowser infovalue functions-----------------------------------------------
def array_infovalue(eng,oname):
    """Numpy array info/value function"""
    shape,dtype = eng.evaluate('( str('+oname+'.shape), str('+oname+'.dtype) )')
    info = 'shape = '+shape+'; dtype = '+dtype
    return info
