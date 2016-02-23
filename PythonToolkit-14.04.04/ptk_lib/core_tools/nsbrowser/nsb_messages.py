"""
Namespace browser message types
"""

#Addressed (to 'NSBrowser') message subjects

#Show the namespace browser pane in the console window, data=(), result=None
SHOW = 'Show'

#Browse to the name given in the engine given, data=(engname, oname), result=None
BROWSE_TO = 'Browse_To'