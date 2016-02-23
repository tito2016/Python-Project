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
#the tool class
from fileio import FileIO

#Other usefull objects/packages
from fileio_misc import Importer, Exporter, FileDrop

from fileio_dialogs import MultipleObjectToFileDialog, DoFileDialog

