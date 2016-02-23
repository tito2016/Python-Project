"""
Engine misc.

Various engine utility functions/classes
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#-------------------------------------------------------------------------------
def get_available_engines():
    """
    Returns a list of available engine types and a dictionary of {engtype strine: description}
    """
    import imp          #dynamic import to keep footprint low.
                        #for checking if gui libaries are installed

    #find which engines are available
    engtypes = []       #list of engtypes strings
    engdescrip = {}     #{engtype string, description string

    #standard python external engine always available 
    engtypes.append('pyEngine')
    engdescrip['pyEngine'] = 'An external engine process without any GUI mainloops running. Interactive use of GUI toolkits will block the console.'

    #check if wxpython is available
    try:
        imp.find_module('wx')
        engtypes.append('wxEngine')
        engdescrip['wxEngine'] = 'An external engine process with the wxPython GUI mainloop running allowing interactive use of the wxPython toolkit.'
    except:
        pass

    #check if Tkinter is available
    try:
        imp.find_module('Tkinter')
        imp.find_module('_tkinter')
        engtypes.append('tkEngine')
        engdescrip['tkEngine'] = 'An external engine process with the Tcl/Tk GUI mainloop running allowing interactice use of the Tcl/Tk toolkit'
    except:
        pass

    #check if gtk is available
    try:
        imp.find_module('gtk')
        engtypes.append('gtkEngine')
        engdescrip['gtkEngine'] = 'An external engine process with the GTK GUI mainloop running allowing interactive use of the pygtk toolkit.'
    except:
        pass

    #check if gtk3 is available
    try:
        imp.find_module('gi')
        engtypes.append('gtk3Engine')
        engdescrip['gtk3Engine'] = 'An external engine process with the GTK3 (pyGObject) GUI mainloop running allowing interactive use of the GTK3 toolkit.'
    except:
        pass

    #check if pyqt4 is available
    try:
        imp.find_module('PyQt4')
        engtypes.append('qt4Engine')
        engdescrip['qt4Engine'] = 'An external engine process with the Qt4 GUI mainloop running allowing interactive use of the pyQt4 toolkit.'
    except:
        pass

    #check if pyside is available
    try:
        imp.find_module('PySide')
        engtypes.append('pysideEngine')
        engdescrip['pysideEngine'] = 'An external engine process with the PySide Qt4 GUI mainloop running allowing interactive use of the PySide toolkit.'
    except:
        pass

    #add internal engine last.
    engtypes.append('Internal')
    engdescrip['Internal'] = 'Internal (debugging) engine runs in the same process as the GUI. Allows interactive use of the wxPython GUI.\nNOTE: Only a single internal engine is allowed and it is always called "Internal".'

    return engtypes, engdescrip

#-------------------------------------------------------------------------------
def get_message_port():
    """
    Get the port used by PTK for communication with engines.
    """
    #dynamic imports to keep footprint small
    import ConfigParser
    import os

    cp = ConfigParser.ConfigParser()
    optionspath = os.getenv("HOME") + os.sep + '.ptk'+os.sep+'options'
    cp.read(optionspath)

    try:
        port = cp.getint('App', 'message_bus_port')
    except ConfigParser.NoOptionError:
        #try default
        port = 6666

    return port

def is_PTK_running():
    """
    Check if PTK is currently running on the local machine.
    """
    #check if lock file exists
    import os
    lock_file = os.getenv("HOME") + os.sep + '.ptk'+os.sep+'PTK-lock'
    lock_exists =  os.path.exists( lock_file )
    if lock_exists is False:
        return False

    with open(lock_file, 'r') as f:
        pid =  f.readline()
    pid = int ( pid.strip('\x00') )

    #check if process is still running
    import platform

    #windows
    if platform.system() == "Windows":

        import ctypes.wintypes
 
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(1, 0, pid)

        #no handle == no process
        if handle == 0:
            return False

        #got a handle check the return code, using window system call
        ret_code = ctypes.wintypes.DWORD()
        res = kernel32.GetExitCodeProcess(handle, ctypes.byref(ret_code))
        kernel32.CloseHandle(handle)
        #res==0 call failed - pid doesn't exist anymore
        #ret_code = 259 - process still running
        return  ( (res != 0) and (ret_code==259) )

    #unix/MacOS
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
 

def start_PTK():
    """
    Attempt to start PTK if not already running, this will look for a previously
    created .ptk folder in the users home folder and use the store path to the
    PTK lauch script.
    
    Returns the pid of the new process.
    """
    #dynamic imports to keep footprint small
    import ConfigParser
    import os
    import subprocess
    cp = ConfigParser.ConfigParser()
    optionspath = os.getenv("HOME") + os.sep + '.ptk'+os.sep+'options'
    cp.read(optionspath)

    try:
        ptk_script = cp.get('App', 'ptk_script_path')
    except ConfigParser.NoOptionError:
        raise Exception('Cannot find PTK lauch script - run PTK manually to set value.')
   
    pid = subprocess.Popen([ptk_script,]).pid
    return pid

#-------------------------------------------------------------------------------
# A general purpose list type object used for storing dictionaries these can 
# then be filtered by key.
# Used to store breakpoints in both the engine debugger (engine process) and
# gui process where breakpoints are stored as dictionaries
class DictList():
    def __init__(self, dicts=(), default={}):
        """
        Create a list like container object for dictionaries with the ability to
        look up dicts by key value or by index.

        dicts - is a sequence of dictionaries to populate the DictList with.
        default - a defualt dictionary to use to create a new dictionary in the 
        list.

        Example.

        >>> person1 = {'Name':'John', 'Age':53}
        >>> person2 = {'Name':'Bob', 'Age':53}
        >>> person3 = {'Name':'Sally', 'Age':31}
        >>> default = {'Name':'', 'Age':0}
        >>> dlist = DictList( (person1,person2,person3),default)

        >>> #Filter by age
        >>> dlist.filter(keys=('Age',),values=(53,))
        [{'Age': 53, 'Name': 'John'}, {'Age': 53, 'Name': 'Bob'}]

        >>> #Filter by age and name
        >>> dlist.filter(keys=('Age','Name'),values=(53,'John'))
        [{'Age': 53, 'Name': 'John'}]

        >>> #Add a new dictionary
        >>> dlist.new()
        {'Age': 0, 'Name': ''}
        """
        self._dicts = []
        for d in dicts:
            self._dicts.append(d)
        self._default = default

    def clear(self):
        """Remove all items"""
        self._dicts = []

    def index(self, d):
        """Find the index of a dictionary in the list"""
        return self._dicts.index(d)

    def pop(self, index):
        """Remove the dictionary at the index given"""
        return self._dicts.pop(index)

    def items(self, key=None):
        """
        Return a list of all dictionaries in the list. If the optional key is 
        given it will returns a list of the values of all dicts which have that 
        key. 
        """
        if key is None:
            return self._dicts

        #get the key values
        dicts = []
        for d in self._dicts:
            if d.has_key(key):
                dicts.append( d[key] )
        return dicts

    def filter(self, keys=(), values=()):
        """
        Filter the dictionaries in the list to return only those
        with all matching key value pairs. 
        """
        dicts = self._dicts
        #filter for each key,value in
        for key, value in zip(keys,values):
            self._fkey = key
            self._fvalue = value
            dicts = filter(self._filter, dicts)
            self._fkey = None
            self._fvalue = None
        return dicts

    def values(self, key):
        """
        Return a list of all values a given key has in the dictionarys.
        """
        values=[]
        for i in self.items():
            value = i[key]
            if value not in values:
                values.append(value)
        return values

    def append(self, d):
        """
        Append a dictionary to the list.
        """
        #check item
        if isinstance(d, dict) is False:
            raise ValueError('Expected a dictionary')
        self._dicts.append(d)

    def new(self):
        """
        Create and append a new dictionary to the list. If a default dictionary 
        has been set a shallow copy will made. The new dictionary is returned.
        """
        d = self._default.copy()
        self.append(d)
        return d

    def remove(self, d):
        """
        Remove the dictionary from the list and return it.
        """
        n= self.index(d)
        return self.pop(n)

    def set_default(self, d):
        if isinstance(d, dict) is False:
            raise ValueError('Default should be a dictionary')

    def _filter(self, d):
        """internal method to find matching items"""
        #d is the dictionary to check for a match
        #self._fkey, self._fvalue are stored before calling this function and
        #are the key:value to match
        if d.has_key(self._fkey):
            return d[self._fkey] == self._fvalue
        else:
            return False

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return self._dicts.__iter__()

    def __getitem__(self, index):
        return self._dicts[n]

    def __setitem__(self, index, d):
        #index store new item
        if isinstance(d, dict) is False:
            raise ValueError('Expected a dictionary')
        self._dicts[index] = d

    def __repr__(self):
        s = 'DictList('+self._dicts.__repr__()+')'
        return s
