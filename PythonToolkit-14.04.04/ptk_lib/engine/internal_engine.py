"""
Internal engine - an engine subclass for the special case of an 
internal (same process) engine. This just uses a MessageBus MBNode to connect to
the message bus and for communication.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#---imports---------------------------------------------------------------------
import time
import sys
from engine import Engine                                   #base class

#-------------------------------------------------------------------------------
class PseudoEvent():
    """
    An object with the same interface as a threading.Event for the internal 
    engine. This prevents the readline/readlines and debugger from blocking
    when waiting for user input.

    This calls the doyield function and sleeps until the event is set.
    """
    def __init__(self, eng):
        self._eng = eng
        self._doyield = eng._doyield
        self._set = False

    def set(self):
        self._set = True

    def clear(self):
        self._set = False

    def wait(self, timeout=None):
        if timeout is not None:
            raise NotImplementedError('Timeout not implemented')
        log.debug('waiting: '+str(self._doyield))
        while (self._set is False) and (self._eng._stop is False):
            self._doyield()
            time.sleep(0.05)

#-------------------------------------------------------------------------------
class InternalEngine(Engine):
    engtype = 'Internal'

    def __init__(self, userdict={}, doyield=None, timeout=10):
        """
        Create an internal engine object.

        userdict    -   Dictionary to execute user commands in.
        doyield     -   A callable to yield to a running mainloop (i.e. wx.Yield)
                        Used to allow the GUI to update and return stdinput and
                        ensure message are sent in the correct order.
        """        
        #call base class init
        Engine.__init__(self, englabel='Internal', userdict=userdict)

        #store reference to the user supplied callables
        self._doyield = doyield

        #for internal engines we need to replace the readevent and debugger
        #resume events and the send_msg/publish_msg methods to allow the GUI 
        #interface a chance to run
        self._readevent = PseudoEvent(self)

    #---------------------------------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.
        """ 
        #call run code directly no need for an event
        self._run_code(code) 

    def get_welcome(self):
        """Return the engines welcome message"""
        welcome = Engine.get_welcome(self) + "\n\nRunning in the interface process\n"
        return welcome

    #---------------------------------------------------------------------------
    def readline(self):
        """std in readline directs here- this calls the stdin handler for input"""
        if self._stop:
            raise KeyboardInterrupt
        return Engine.readline(self)

    def readlines(self):
        """std in readlines directs here"""
        if self._stop:
            raise KeyboardInterrupt
        return Engine.readlines(self)

    def write_stdout(self,string):
        """std out write redirects here"""
        if self._stop:
            raise KeyboardInterrupt
        Engine.write_stdout(self, string)

    def write_stderr(self,string):
        """std err write redirects here"""
        if self._stop:
            raise KeyboardInterrupt
        sys.__stdout__.write(string)
        Engine.write_stderr(self, string)

    def enable_debug(self,flag=True):
        """ 
        Enable the debugger - returns debug state 
        Not available in internal engine so always return False        
        """
        self.write_stderr('Debugger is not available in Internal engine')
        return False

    #---------------------------------------------------------------------------
    def on_disconnect(self):
        """
        Overloaded on_disconnect method of client to preform engine tasks
        """
        Engine.on_disconnect(self)

        # stop any running user code
        self.stop_code(quiet=True)

    def on_err_disconnect(self):
        """
        Overloaded on_err_disconnect method to call both base classes
        """
        Engine.on_err_disconnect(self)

        # stop any running user code
        self.stop_code(quiet=True)

