"""
Inspector engine tasks:

Engine tasks for getting object info from the engine
"""
def get_object_category(globals, locals,oname):
    import inspect
    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return None
    if inspect.isclass(obj):
        return 'type'
    if inspect.isroutine(obj):
        return 'routine'
    if inspect.ismodule(obj):
        return 'module'
    try:
        if obj.__module__+'.'+obj.__type__ == 'numpy.ufunc':
            return 'routine'
    except:
        pass
    return 'instance'

def get_type_info(globals, locals,oname):
    import inspect

    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return None   
   
    #check it's a class
    if inspect.isclass(obj) is False:
        return None
    #data to return
    data={}

    #get name and module
    t = type(obj)
    data['type_name'] = getattr( t,'__name__',str(t))
    data['type_module'] = getattr(t, '__module__',None)
    if data['type_module'] is None:
        data['type_module'] = ''
        data['type'] = data['type_name']
    else:
        data['type'] = data['type_module']+'.'+data['type_name']

    #object name string
    name = getattr(obj,'__name__',str(obj))
    module = getattr(obj,'__module__',None)
    if module in [None,'']:
        data['obj_name'] = name
    else:
        data['obj_name'] = module+'.'+name

    #doc string
    data['doc'] = getattr(obj,'__doc__',None)
    if data['doc'] is None:
        data['doc']='No Docstring.'

    #get constructor args and docstring
    def get_constructor(object):
        try:
            return object.__init__
        except AttributeError:
            try:
                for base in object.__bases__:
                    constructor = get_constructor(base)
                    if constructor is not None:
                        return constructor
            except:
                constructor = None
        return None
    
    con = get_constructor(obj)
    if con is None:
        data['conargspec'] = 'Unknown'
        data['condoc']     = None
    else:
        data['condoc'] = getattr(con, '__doc__', None)
        try:
            conargs = inspect.getargspec(con)
            if conargs[0][0]=='self':
                conargs[0].pop(0)
            data['conargspec'] = oname+apply(inspect.formatargspec, conargs)
        except:
            data['conargspec'] = 'Unknown'

    if data['condoc'] is None:
        data['condoc'] = 'No constructor docstring'

    #source file
    try:
        data['sourcefile'] = inspect.getsourcefile(obj)
    except:
        data['sourcefile'] = None
    
    #source
    try:
        data['source'] = inspect.getsource(obj)
    except:
        data['source'] = 'Not available.'

    return data

def get_routine_info(globals, locals,oname):
    import inspect
        
    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return None      
    data={}

    #check a routine
    if inspect.isroutine(obj) is False:
        return None

    #get name and module
    t = type(obj)
    data['type_name'] = getattr( t,'__name__',str(t))
    data['type_module'] = getattr(t, '__module__',None)
    if data['type_module'] is None:
        data['type_module'] = ''
        data['type'] = data['type_name']
    else:
        data['type'] = data['type_module']+'.'+data['type_name']

    #object name string
    name = getattr(obj,'__name__',str(obj))
    module = getattr(obj,'__module__',None)
    if module in [None,'']:
        data['obj_name'] = name
    else:
        data['obj_name'] = module+'.'+name

    #argspec
    try:
        conargs = inspect.getargspec(obj)
        if conargs[0][0]=='self':
            conargs[0].pop(0)
        data['argspec'] = oname+apply(inspect.formatargspec, conargs)
    except:
        data['argspec'] = 'Unknown'

    #doc string
    data['doc'] = getattr(obj,'__doc__',None)
    if data['doc'] is None:
        data['doc']='No Docstring.'

    #source file
    try:
        data['sourcefile'] = inspect.getsourcefile(obj)
    except:
        data['sourcefile'] = None
    
    #source
    try:
        data['source'] = inspect.getsource(obj)
    except:
        data['source'] = 'Not available.'

    return data

def get_module_info(globals, locals,oname):
    import inspect
        
    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return None      
    data={}
    #check a module
    if inspect.ismodule(obj) is False:
        return None
    
    #object name string
    name = getattr(obj,'__name__',str(obj))
    module = getattr(obj,'__module__',None)
    if module in [None,'']:
        data['obj_name'] = name
    else:
        data['obj_name'] = module+'.'+name

    #module doc string
    data['doc'] = getattr(obj,'__doc__',None)
    if data['doc'] is None:
        data['doc']='No Docstring.'

    #source file
    try:
        data['sourcefile'] = inspect.getsourcefile(obj)
    except:
        data['sourcefile'] = None
    
    #source
    try:
        data['source'] = inspect.getsource(obj)
    except:
        data['source'] = 'Not available.'

    return data

def get_instance_info(globals, locals,oname):
    import inspect
        
    #get a ref to the object
    try:
        obj = eval(oname,globals, locals)
    except:
        return None      
    data={}

    #get name and module
    t = type(obj)
    data['type_name'] = getattr( t,'__name__',str(t))
    data['type_module'] = getattr(t, '__module__',None)
    if data['type_module'] is None:
        data['type_module'] = ''
        data['type'] = data['type_name']
    else:
        data['type'] = data['type_module']+'.'+data['type_name']

    #object value string
        
    return data
