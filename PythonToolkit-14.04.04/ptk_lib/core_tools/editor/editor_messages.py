"""
Messages types for the editor tool
"""

#Addressed (to 'Editor') messages

#Open the file(s) in the editor, data=filenames, result=None
EDITOR_OPEN = 'Open'

#Open a new file(s) in the editor, data=filenames, result=None
EDITOR_NEW  = 'New'

#Show the editor frame, data=(), result=None
EDITOR_SHOW = 'Show'

#Hide the editor frame, data=(), result=None
EDITOR_HIDE = 'Hide'

#Published by editor messages
#Published when a new breakpoint is set by the enginemanager, 
# data=(id,bpdata)
EDITOR_BREAKPOINT_SET = 'Editor.Breakpoint.Set'

#Published when a breakpoint is cleared, data=(id,)
# if id is None - all have been cleared.
EDITOR_BREAKPOINT_CLEARED = 'Editor.Breakpoint.Cleared'

#Published when a breakpoint is changed, 
# data=(id, kwargs=dictionary of changed values)
EDITOR_BREAKPOINT_CHANGED = 'Editor.Breakpoint.Changed'
