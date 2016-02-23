"""
Message types for the views tool.
"""

#Addressed (to 'Views') message subjects

#Sent to open a gui of the object name, data=(engname, oname), result=None
OPENVIEW = 'OpenView'

#Sent to check if a gui view exists for the object type, data=(type_string,), result=None
HASVIEW = 'HasView'
