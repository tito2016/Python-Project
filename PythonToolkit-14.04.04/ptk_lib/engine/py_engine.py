"""
pyEngine:

A basic python engine for use with PTK with no gui mainloops running
- uses a threading.Event() object to wake mainloop and run user command.
"""
#---Logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------
import threading
from engine import Engine

class pyEngine(Engine):
    engtype = 'PTK.py'

    def __init__(self, englabel=None, userdict={}, 
                    timeout=10):

        Engine.__init__(self, englabel, userdict, timeout)

        #---setup an event to indicate code to run------------------------------
        self._codeevent = threading.Event() #event to indicate code to run
        self._code = None  #code object to run in mainloop as the user
        self._exit = False #exit flag

    #---Main interface----------------------------------------------------------
    def start_main_loop(self):
        """Wait for user commands to execute"""
        if self.connected is False:
            raise Exception('Not connected to MessageBus!')

        while True:
            #check exit flag
            if self._exit is True:
                break

            #wait for code event or exit
            self._codeevent.wait()
            
            #check exit again
            if self._exit is True:
                break

            #run code
            self._run_code(self._code) 
            self._code = None
            self._codeevent.clear()

        log.info('Mainloop ended')

    #---overload base methods---------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.
        """ 
        #have a code object so store it and set event
        self._code=code 
        self._codeevent.set()

    def on_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will wake the main loop.
        """
        Engine.on_disconnect(self)
        log.info('Exiting process')
        self._exit = True
        self.stop_code(quiet=True)
        self._codeevent.set() #trigger the event to wake up the mainloop

    def on_err_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will wake the main loop.
        """
        Engine.on_err_disconnect(self)
        log.info('Exiting process')
        self._exit = True
        self.stop_code(quiet=True)
        self._codeevent.set() #trigger the event to wake up the mainloop

    def get_welcome(self):
        """Return the engines welcome message"""
        welcome = Engine.get_welcome(self) + "\n\nRunning as an external engine process\n"
        return welcome

