"""
gtk engine

An external engine running the gtk mainloop.

More complex than other engines as gtk acquires the python GIL before
calling a python handler preventing the communications thread from running.

Solution: Use gtk.gdk.threads_* functions to allow threads with gtk.

    gtk.gdk.threads_init()  
    gtk.main()

"""
#---Logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#-------------------------------------------------------------------------------
from gi.repository import Gtk, Gdk, GObject


from engine import Engine

class gtkEngine(Engine):
    engtype='Embedded.gtk3'
    def __init__(self, parent, englabel=None, userdict={}, 
                    timeout=10):
        """
        The PTK engine class for embedding in gtk3 (pyGObject) applications. 
        To use create an instance of this or a subclass. 
        It uses the parent object for signals. 
        engine.disconnect() should also be called before the application exits.
        
        Important. 
        It uses the a the gtk mainloop to post/bind events and starts a 
        communications thread, therefore gtk.gdk.threads_init() must be called 
        before the main loop is started!

            GObject.threads_init() 
            Gtk.main()

        Signals to use:
        'engine_disconnect' -  sent went the engine disconnects.

        Methods/attributes you might want to overload:
        _get_welcome()  - Returns a string welcome message.
        self.eng_prompts - these are the prompts used by the controlling console.
        """
        self.parent = parent
        
        #add the engine disconnect signal
        if GObject.signal_lookup("engine_disconnect", self.parent) == 0:
            GObject.signal_new("engine_disconnect", self.parent, 
                               GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,())
        Engine.__init__(self, englabel, userdict, timeout)

    #---overloaded base methods-------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.
        """ 
        #run the code in main thread.
        GObject.idle_add(self.idle_code, code)

    def on_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will emit a "engine_disconnect" signal after preforming standard
        engine disconnect tasks
        """
        Engine.on_disconnect(self)
        GObject.idle_add(self.parent.emit, "engine_disconnect")

    def on_err_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will emit a "engine_disconnect" signal after preforming standard
        engine disconnect tasks
        """
        Engine.on_err_disconnect(self)
        GObject.idle_add(self.parent.emit, "engine_disconnect")

    def get_welcome(self):
        """Return the engines welcome message"""
        welcome = Engine.get_welcome(self) + "\n\nRunning as an external engine process with a GTK3 mainloop\n"
        return welcome

    #---------------------------------------------------------------------------
    def idle_code(self,code):
        #run code - but make sure we have the GDK lock first...
        Gdk.threads_enter()
        self._run_code(code)
        Gdk.threads_leave()

             
#-------------------------------------------------------------------------------
# Subclass used for standalone engine
#-------------------------------------------------------------------------------
class PTK_gtk3Engine(gtkEngine):
    engtype = 'PTK.gtk3'
    def __init__(self, englabel=None, userdict={}, 
                    timeout=10):
        """
        The gtkEngine object used for a standalone PTK engine. 
        It creates handles the engine_close signal to end the mainloop.
        """
        self.gobj = GObject.GObject()
        gtkEngine.__init__(self, self.gobj, englabel, userdict, timeout)

        #handle the engine_disconnect signal
        self.gobj.connect("engine_disconnect", self.on_eng_disconnect)

    #---Main interface----------------------------------------------------------
    def start_main_loop(self):
        """Wait for user commands to execute"""
        if self.connected is False:
            raise Exception('Not connected to MessageBus!')

        #release the python Global interpretor lock to allow comms to work!
        GObject.threads_init()  
        Gtk.main()
        log.info('Mainloop ended')

    #---------------------------------------------------------------------------
    def on_eng_disconnect(self, engine):
        self.stop_code(quiet=True)
        Gtk.main_quit()
