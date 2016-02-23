"""
Misc classes used in the FileIO system

FileDrop    - A wxFileFropTarget, that can use the FileIO system to determine 
                what to do with the dropped file.
Importer    - A class containing information about file and data importers.
Exporter    - A class containing information about Data exporters.
"""
import wx

#-------------------------------------------------------------------------------
# FileDrop - a drop target for use in various places. Uses the message_bus 
# system and FileIO core tool to open files.
#-------------------------------------------------------------------------------
class FileDrop(wx.FileDropTarget):
    def __init__(self, openfunc=None):
        """
        Create a file drop target which either called the openfunc or if None
        uses the default fileIO system which will attempt to open the file
        in the registered handler.
        """
        wx.FileDropTarget.__init__(self)
        self.openfunc = openfunc

    def OnDropFiles(self, x, y, filenames):
        if self.openfunc==None:
            wx.GetApp().msg_bus.send_msg('FileIO','Open', filenames)
        else:
            for filename in filenames:
                self.openfunc(filename)

#-------------------------------------------------------------------------------
# Importer base class
#-------------------------------------------------------------------------------
class Importer():
    def __init__(self, name, file_exts, data=False, wildcards=[], descrip=''):
        """
        Create an importer for the filetypes given by the dict of file_exts.
        
        name        -   the name/short description string to display for this 
                        importer e.g. 'Open in editor'
        file_exts   -   dict of file extensions and descriptions e.g. 
                        'txt':'Text file'
        data        -   True/False flag indicating whether this is a python data 
                        importer
        wildcards   -   A list of wildcard string to display in file open dialog ( e.g.
                        'Text (.txt)|*.txt') used for the data import file dialog.
        descrip     -   a long description string.
        """
        self.name = name
        self.file_exts = file_exts
        self.data = data
        self.wildcards = wildcards
        self.descrip = descrip
        self.app = wx.GetApp()
        self.msg_bus = self.app.msg_bus

    def __call__(self, filename):
        """
        Overload this method to define what happens when the importers is called.
        """
        pass

    def get_name(self):
        """
        Get the importer name
        """
        return self.name

    def get_file_exts(self):
        return self.file_exts

    def get_description(self):
        return self.descrip

    def get_wildcards(self):
        """
        Returns a list of wildcard strings to use in file dialogs
        """
        return self.wildcards
        
#-------------------------------------------------------------------------------
# Exporter base class
#-------------------------------------------------------------------------------
class Exporter():
    def __init__(self, name, type_strings, descrip=''):
        """
        Create an exporter for the types given by the list of type_strings.
        name            - the name string to display for this exporter (in menus etc)
        type_strings    - list of supported python object type_strings.
        descrip         - descritpion string to display in dialog
        """
        self.name = name
        self.type_strings = type_strings
        self.descrip = descrip
    
        self.app = wx.GetApp()
        self.msg_bus = self.app.msg_bus

    def __call__(self, engname, onames):
        """
        Overload this method to export the objects given.
        Where engname is the engine to export from, onames is a list of object names
        """
        pass

    def get_name(self):
        return self.name

    def get_types(self):
        return self.type_strings

    def get_description(self):
        return self.descrip
