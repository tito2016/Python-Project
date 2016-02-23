"""
Message types for the FileIO tool
"""

#Addressed messages sent to 'FileIO'

#Open the file(s) using the fileio system, data=filenames, result=None
OPEN = 'Open'

#Export data from a python engine, data= (engname, onames), result=None
EXPORT = 'Export'

#Import data from a file, data=(), result=None
IMPORT = 'Import'