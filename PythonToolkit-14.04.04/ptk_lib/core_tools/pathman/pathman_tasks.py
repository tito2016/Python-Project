"""
PathManager engine tasks:

EngineTask subclasses for controlling the current working directory and sys.path
"""

#---Get the sys.path------------------------------------------------------------
def get_sys_path(globals, locals):
    import sys
    return sys.path

#---Add to sys.path-------------------------------------------------------------
def add_to_sys_path(globals, locals, path):
    import sys
    if sys.path.count(path)==0:
        sys.path.append(path)
    #return a copy of the sys.paths
    return sys.path

#---Remove from sys.path--------------------------------------------------------
def remove_from_sys_path(globals, locals, path):
    import sys
    if sys.path.count(path)!=0:
        n = sys.path.index(path)
        old = sys.path.pop(n)
    #return a copy of the sys.paths
    return sys.path

#---Move up sys.path------------------------------------------------------------
def move_up_sys_path(globals, locals, path):
    import sys
    if sys.path.count(path)!=0:
        n = sys.path.index(path)
        if n!=0:
            sel = sys.path.pop(n)
            newn = n-1
            sys.path.insert(n-1,sel)
        else:
            newn = n
    #return a copy of the sys.paths
    return sys.path,newn

#---Move down sys.path----------------------------------------------------------
def move_down_sys_path(globals, locals, path):
    import sys
    if sys.path.count(path)!=0:
        n = sys.path.index(path)
        if n!=len(sys.path):
            sel = sys.path.pop(n)
            newn = n+1
            sys.path.insert(n+1,sel)
        else:
            newn = n
    #return a copy of the sys.paths
    return sys.path,newn


