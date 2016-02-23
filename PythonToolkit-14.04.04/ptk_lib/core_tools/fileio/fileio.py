"""
FileIO
------
A service tool to handle requests to open files and import/export data.
It has three main actions:

1)Opening Files:

When a component wishes to open a file (for example that has been dropped on a 
window), it sends a message to FileIO.FileOpen with data = filepath. 
The filepath is then either passed to a registered importer or if multiple 
importers are registered offers a choice dialog.

To register a file type - use register_importer()

2) Importing data:
Data importer can also be used to import data from files.

3) Exporting data:
Tools can also register data exporters and which python object types it can handle.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.INFO)

#---Imports---------------------------------------------------------------------
import os
import wx

from ptk_lib.tool_manager import Tool
from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.resources import ptk_icons

from fileio_misc import Importer, Exporter
from fileio_dialogs import ExportDialog, DoFileDialog
import fileio_messages

from pickle_io import PickleExporter, PickleImporter

#-------------------------------------------------------------------------------
class FileIO(Tool):
    name = 'FileIO'
    descrip = 'Core tool providing file import/export'  
    author = 'T.Charrett'
    requires = []           
    core = True            
    icon = None
    def __init__(self):
        Tool.__init__(self)
        log.info('Initialising tool')
    
        #---File importers -----------------------------------------------------
        #list of importers - used for opening files
        self.importers = []

        #---exporters-----------------------------------------------------------
        #list of registered python type exporters 
        self.exporters = []

        #add standard exporters/importers
        self.register_exporter( PickleExporter() )
        self.register_importer( PickleImporter() )

        #---Messages------------------------------------------------------------
        #create a message bus node for this tool
        self.msg_node = MBLocalNode('FileIO')
        self.msg_node.connect(self.msg_bus)
        
        #Register message handlers
        self.msg_node.set_handler(fileio_messages.OPEN,   self.msg_open) #open the named file
        self.msg_node.set_handler(fileio_messages.EXPORT, self.msg_export) #export objects to file
        self.msg_node.set_handler(fileio_messages.IMPORT, self.msg_import) #import objects from a file

        log.info('Done Initialising tool')

    #---Interfaces--------------------------------------------------------------
    def register_importer(self, importer):
        """
        Register an Importer object with the FileIO system
        """
        log.debug('Registering importer "'+importer.name+'"')
        self.importers.append(importer)

    def get_importers(self, file_ext, data_only=False):
        """
        Get a list of registered importers that can handle the file type given by
        file_ext. If data_only is True only python data importers for the type 
        will be returned.
        """
        valid = []
        for imp in self.importers:
            if file_ext in imp.file_exts:
                valid.append(imp)
        if data_only is False:
            return valid

        data_valid = []
        for imp in valid:
            if imp.data is True:
                data_valid.append(imp)
        return data_valid

    def open_file(self,filepath, parent=None):
        """
        Opens the file specified using the registered importers
        parent is an optional wxwindow to use as the parent to the choice dialog
        """
        console = self.toolmgr.get_tool('Console')

        file_ext = os.path.splitext(filepath)[1]
        importers = self.get_importers(file_ext)

        #one importer
        if len(importers)==1:
            log.debug('Found registered importer for file: '+str(filepath))
            importer = importers[0]
            importer(filepath)
            return

        #no importers or multiple importers - show choice dialog
        if len(importers)==0:
            log.debug('No registered importers found for file: '+str(filepath))
            title = 'No file importer for file:'
            importers = self.importers
        else:
            log.debug('Found multiple file importers for file: '+str(filepath))
            title = 'Multiple file importers found:'
        #list of helptips to display
        choices = []
        for imp in importers:
            choices.append(imp.name)
        #create and show dialog
        dlg = wx.SingleChoiceDialog( None, 'Open with: ', 
                                     title,
                                     choices, wx.CHOICEDLG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            n = dlg.GetSelection()
            imp = importers[n]
            imp(filepath)
        dlg.Destroy()

    def import_data(self):
        """
        Import data using the registered data importers. Similiar to open_file
        but this displays a dialog showing ONLY data importers
        """
        console = self.toolmgr.get_tool('Console')
        eng = console.get_current_engine()
        #no active engine - do nothing
        if eng is None:
            return

        #get data importers
        importers = []
        for imp in self.importers:
            if imp.data is True:
                importers.append(imp)
        #create data importers wildcard string
        wildcard = ''
        imp_index=[]
        for imp in importers:
            imp_wildcards = imp.get_wildcards()
            for imp_wildcard in imp_wildcards:
                #add wildcard string and reference to importer in list
                wildcard = wildcard + imp_wildcard+'|'
                imp_index.append(imp)
        wildcard=wildcard[0:-1] #remove final |

        #open file dialog
        dlg = wx.FileDialog(
                console.frame, message='Select file to import:',
                defaultFile="",
                wildcard = wildcard,
                style= wx.OPEN | wx.FILE_MUST_EXIST
                )
        if dlg.ShowModal() != wx.ID_OK:
            return
        # get the enetered file path
        filepath = dlg.GetPath()
        imp = imp_index[ dlg.GetFilterIndex() ]
        dlg.Destroy()
        #call importer
        log.debug(str(filepath)+str(imp))
        imp(filepath)

    #Data exporters
    def register_exporter(self, exporter):
        """
        Register a new Exporter object for python types given in the list of 
        type strings in Exporter.type_strings.
        """
        log.debug('Registering exporter "'+exporter.name+'"')
        self.exporters.append(exporter)

    def get_exporters(self):
        """
        Returns a list of all available exporters
        """
        return self.exporters

    def export_data(self, engname=None, onames=[]):
        """
        Open the exporter dialog for the engname with the onames given
        pre-selected. If engname is None the current engine is initially 
        selected.
        """
        if engname is None:
            console = self.toolmgr.get_tool('Console')
            engname = console.get_current_engname()
        #no engines - do nothing
        if engname is None:
            return
        #open the export dialog
        d = ExportDialog(engname,onames)
        id = d.ShowModal()
        
        #call exporter
        if id==wx.ID_OK and d.exporter is not None:
            res = d.exporter( d.engname, d.GetObjectNames())
        d.Destroy()

    #---message handlers--------------------------------------------------------
    def msg_open(self,msg):
        """Handlers file open requests"""
        filepaths = msg.get_data()
        for filepath in filepaths:
            self.open_file(filepath)

    def msg_export(self,msg):
        """Handler for export message"""
        engname,onames = msg.get_data()
        self.export_data(engname,onames)

    def msg_import(self,msg):
        """Handler for import message"""
        self.import_data()



