"""
Engine Tasks

An engine task is a more complex operation to perform inside the engine process,
such as setting a python path in sys.paths...

The code to do the operation should be enclosed within a function that takes two
arguments:

Task(globals,*args,*kwargs)

userditc is supplied by the engine process and is the users namespace dictionary
args are the task secific arguments. For example a task to add to the sys path 
would look like.

def AddPath(userdict,path):
    import sys
    sys.paths.append(path)

"""
#---common tasks----------------------------------------------------------------
def object_exists(globals, locals, name):
    """
    Engine task to check if an object exists in th users namespace
    """
    try:
        obj = eval(name, globals, locals)
        res = True
    except:
        res = False
    return res

def get_type_string(globals, locals, name):
    """
    Engine task to return the type string of an object
    """
    try:
        obj = eval(name, globals, locals)
        #get type_string
        t = type(obj)
        type_string = t.__module__ + '.' + t.__name__
    except:
        type_string = 'UNKNOWN'
    return type_string

def execute_startup_script(globals, locals):
    """
    Engine task to execute the python startup script
    """
    import os
    startup = os.environ.get('PYTHONSTARTUP')
    if startup and os.path.isfile(startup):
        text = '\nStartup script executed: ' + startup +'\n'
        line = 'execfile(%r)' % (startup)
        execfile(startup,globals, locals)
        print text
        return True
    else:
        return False

def get_cwd(globals, locals):
    """
    Engine task to get current working directory
    """
    import os
    curdir = os.getcwd()
    return curdir

def set_cwd(globals, locals,path):
    """
    Engine task to set current working directory
    """
    import os
    if os.path.exists(path):
        os.chdir( path)
        ok = True
    else:
        ok = False
    return ok

