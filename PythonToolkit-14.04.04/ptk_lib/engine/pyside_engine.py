"""
PySide Qt4 External engine using the pySide bindings.

uses the Qt4 mainloop and signals to run user commands.
"""
#---Logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#-------------------------------------------------------------------------------
from PySide import QtCore, QtGui

from engine import Engine

#gui yield = self.app.processEvents()

SigCode = 'UserCode()'
SigDisconnect = 'UserDisconnect()'

class pysideEngine(Engine):
    engtype='Embedded.pyside'
    def __init__(self, parent, englabel=None, userdict={}, 
                    timeout=10):
        """
        The PTK engine class for embedding in pyside applications. 
        To use create an instance of this or a subclass. 
        It uses the parent object to for signals. 
        engine.disconnect() should also be called before the application exits.

        Signals to use:
        SigDisconnect -  sent went the engine disconnects.

        Methods/attributes you might want to overload:
        get_welcome()  - Returns a string welcome message.
        self.eng_prompts - these are the prompts used by the controlling console.
        """
        Engine.__init__(self, englabel, userdict, timeout)

        self._code = None
        self.parent = parent
        self.parent.connect(self.parent, QtCore.SIGNAL(SigCode), self.on_code)


    #---overload base methods---------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.
        """ 
        self._code = code
        self.parent.emit(QtCore.SIGNAL(SigCode))

    def on_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will emit a SigDisconnect signal.
        """
        Engine.on_disconnect(self)
        self.parent.emit(QtCore.SIGNAL(SigDisconnect))

    def on_err_disconnect(self):
        """
        The engine node disconnected from the message bus.
        This will emit a SigDisconnect signal.
        """
        Engine.on_err_disconnect(self)
        self.parent.emit(QtCore.SIGNAL(SigDisconnect))

    def get_welcome(self):
        """Return the engines welcome message"""
        welcome = Engine.get_welcome(self) +"\n\nRunning as an external engine process with a PySide qt4 mainloop\n"
        return welcome

    #---qt slot event handler---------------------------------------------------
    def on_code(self):
        #run code
        self._run_code(self._code) 
        self._code = None

#---Subclass for PTK engine-----------------------------------------------------
class PTK_pysideEngine(pysideEngine):
    engtype = 'PTK.pyside'
    def __init__(self, englabel=None, userdict={}, 
                    timeout=10):
        """
        The pysideEngine object used for a standalone PTK engine. 
        It creates its own QApplication object.
        """
        self.app = QtGui.QApplication([])
        self.app.setApplicationName('PTK PySide Qt4 engine')
        self.app.setQuitOnLastWindowClosed(False)

        #handle the SigDisconnect signal
        self.app.connect(self.app, QtCore.SIGNAL(SigDisconnect), self.on_eng_disconnect)

        pysideEngine.__init__(self, self.app, englabel, userdict, timeout)

    #---Main interface----------------------------------------------------------
    def start_main_loop(self):
        """Wait for user commands to execute"""
        if self.connected is False:
            raise Exception('Not connected to MessageBus!')
        self.app.exec_()

    #---qt slot event handler---------------------------------------------------
    def on_eng_disconnect(self):
        self.stop_code(quiet=True)
        self.app.exit()
