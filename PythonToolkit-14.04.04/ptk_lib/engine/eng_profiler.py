"""
Engine profiler

calls = { called function name : (calls={}, tic, toc)}

    

TODO: Everything!!!!!
"""

#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

import sys
from threading import Event             #for readline events
import thread                           #to interupt, running code.
import time                             #to time code
import inspect                          #for frame inpsection

import eng_messages                     #standard engine message types

class EngineProfiler():
    def __init__(self, eng):
        #-----------------------------------------------------------------------
        # Attributes
        #-----------------------------------------------------------------------
        self.eng = eng                  #parent engine

        #wxpython raises a different error than keyboard interupt catch it use a
        #stop flag check on exception.
        self._stop = False

    #---------------------------------------------------------------------------
    # Interface methods
    #---------------------------------------------------------------------------
    def profile_code(self, code):
        """Run the user code in the debugger"""

        #turn profile on
        sys.setprofile(self._profile)

        #run the code
        try:
            exec code in self.eng._user_globals, self.eng._user_locals

        #system exit  - close engine
        except SystemExit:
            log.debug('system exit in runnning code')
            sys.setprofile(None)
            self.eng._busy = False
            self.eng.close()

        #keyboard interrupt - stop running code
        except KeyboardInterrupt:
            sys.setprofile(None)
            self.eng._busy = False
            #engine stopped code to exit
            if self.eng._exiting:
                return
            #user stopped code
            self._on_stop()

        #other exception
        except:
            sys.setprofile(None)
            self.eng._busy = False
            #engine is exiting   -  probably some error caused by engine exiting
            if self.eng._exiting:
                log.exception('Exception raised to stop running code? - engine wants to exit.')
                return

            #engine wanted to stop - probably wxPython keyboard interrupt error
            if self._stop is True:
                self._on_stop()

            #error in user code.
            self._showtraceback()

        sys.setprofile(None)

    def stop_code(self):
        """ Stop currently running code """
        #try a keyboard interrupt - this will not work for the internal engine 
        # as the error is raised here instead of the running code, hence put in 
        #try clause.
        try:
            thread.interrupt_main()
        except:
            pass

        #if that doesn't work set the stop flag and wake the traceback function
        #if necessary
        self._stop=True  

    #---------------------------------------------------------------------------
    # Internal methods
    #---------------------------------------------------------------------------
    def _on_stop(self):
        """called when user stopped code"""
        sys.stderr.write('STOP: User forced running code to stop.\n\n')
        #publish engine stopped message
        try:
            data = (self.eng.engname,)
            self.eng.publish_msg( eng_messages.ENGINE_STOPPED,data)
        except:
            log.exception('Cannot publish message!')
        self._stop = False

    def _profile(self,frame, event, arg):
        tb = inspect.getframeinfo(frame)
        if event=='call':
            #self.current_scope = 
            pass
        elif event=='return':
            pass
