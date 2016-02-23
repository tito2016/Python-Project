"""
Namespace browser engine tasks:

EngineTask subclasses for getting infomation about objects
"""

#---clear main namespace task---------------------------------------------------
def clear_main(globals, locals):
    dirlist = locals.keys()
    n = dirlist.index('__builtins__')
    dirlist.pop(n)
    for name in dirlist:    
        exec('del '+name,globals, locals)
    return True

#---Copy item task--------------------------------------------------------------
def copy_object(globals, locals, oname, new):
    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return False
    if hasattr(obj,'copy'):
        cmd = new+'='+oname+'.copy()'
    else:
        cmd = new+'='+oname
    exec(cmd, globals, locals)
    return True

#---Rename item task------------------------------------------------------------
def rename_object(globals, locals, oname, new):
    #get a ref to the object
    try:
        obj = eval(oname, globals, locals)
    except:
        return False
    exec( new+'='+oname, globals, locals)
    exec( 'del '+oname, globals, locals)
    return True

#---Get dir listing details for the namespace browser---------------------------
def get_dir_list(globals, locals, address):
    """
    Get the namespace browser dirlisting.
    """    
    import inspect

    if address in ['',u'']:
        #get the names from the locals and globals
        names = locals.keys()
        for name in globals.keys():
            #only add global name if not already in the locals
            if name not in names:
                names.append(name)
    else:
        #get the object
        obj = eval(address, globals, locals)
        names = dir(obj)

    #print locals.keys(), globals.keys()
    #try:
    #    #this will not work if __builtins__ has been deleted by the user!
    #    names = eval('__builtins__.dir('+address+')',globals, locals)
    #except:
    #    names = []

    dirlist = []

    for name in names:
        try:
            #get the object
            if address!='':
                oname = address+'.'+name
            else:
                oname = name
            obj = eval(oname, globals, locals)
                
            #get flags
            istype = inspect.isclass(obj)
            isrout = inspect.isroutine(obj)
            ismod  = inspect.ismodule(obj)
            isinst = not (istype or isrout or ismod)

            #get type_string
            t = type(obj)
            type_string = t.__module__ + '.' + t.__name__
        except:
            type_string = 'UNKNOWN'
            istype = True
            isrout = True
            ismod  = True
            isinst = True
        #add to listing
        dirlist.append( (name,type_string,istype,isrout,ismod,isinst) )
    
    #return the results
    return dirlist

