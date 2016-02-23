"""
Tkinter engine

uses the Tk mainloop and events to run user commands.
"""
#---Logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#-------------------------------------------------------------------------------
import Tkinter as tk
from engine import Engine
#-------------------------------------------------------------------------------

EvtCode  = "<<ENGINE_CODE>>"
EvtDisconnect = "<<ENGINE_DISCONNECT>>"

#-------------------------------------------------------------------------------
#GUI yield - self.root.update

class TkEngine(Engine):
    engtype='Embedded.Tk'
    def __init__(self, parent, englabel=None, userdict={}, 
                    timeout=10):
        """
        The PTK engine class for embedding in TkInter applications. 
        To use create an instance of this or a subclass. 
        It uses the parent object to post.bind events.
        engine.disconnect() should also be called before the application exits.

        Evts to use:
        EvtDisconnect = "<<ENGINE_DISCONNECT>>" sent went the engine disconnects

        Methods/attributes you might want to overload:
        _get_welcome()  - Returns a string welcome message.
        self.eng_prompts - these are the prompts used by the controlling console.
        """
        Engine.__init__(self, englabel, userdict, timeout)
        self.parent = parent
        self._code = None

        #bind events
        self.parent.bind(EvtCode, self.on_engine_code)

    #---overload base methods---------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.
        """ 
        self._code = code
        self.parent.event_generate(EvtCode,when='tail')

    def on_disconnect(self):
        """
        Called automatically when the engine messagebus node exits/closes.
        This will emit a EvtDisconnect event.
        """
        Engine.on_disconnect(self)
        self.parent.event_generate(EvtDisconnect, when='tail')

    def on_err_disconnect(self):
        """
        Called automatically when the engine messagebus node exits/closes.
        This will emit a EvtDisconnect event.
        """
        Engine.on_err_disconnect(self)
        self.parent.event_generate(EvtDisconnect, when='tail')

    def get_welcome(self):
        """Return the engines welcome message"""
        welcome = Engine.get_welcome(self) + "\n\nRunning as an external engine process with a Tk mainloop\n"
        return welcome

    #---tk event handlers-------------------------------------------------------
    def on_engine_code(self,event):
        #run code
        self._run_code(self._code) 
        self._code = None

#---PTK standalone engine subclass----------------------------------------------
class PTK_TkEngine(TkEngine):
    engtype='PTK.Tk'
    def __init__(self, englabel=None, userdict={}, 
                    timeout=10):
        """
        The tkEngine object used for a standalone PTK engine. 
        It creates its own tk.Tk root object.
        """
        #Tk root object
        self.root = tk.Tk(className='PTK_root')

        #handle close events
        self.root.bind( EvtDisconnect, self.on_engine_disconnect)

        #prevent root window from displaying
        self.root.withdraw()
    
        TkEngine.__init__(self, self.root, englabel, userdict, timeout)

    #---Main interface----------------------------------------------------------
    def start_main_loop(self):
        """Wait for user commands to execute"""
        if self.connected is False:
            raise Exception('Not connected to MessageBus!')
        self.root.mainloop()

    #---tk event handlers-------------------------------------------------------
    def on_engine_disconnect(self,event):
        self.stop_code(quiet=True)
        self.root.quit()
