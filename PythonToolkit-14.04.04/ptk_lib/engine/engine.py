"""
The engine is the object that actually executes user commands and handles 
debugger and profiler functions. It can exist in a seperate process (external 
engines) or within the interface process (internal engine) and is a subclass of 
MBClient for commuications with it's console and other PTK tools. 

This allows other extensions to be added to the engine by defining new message 
types and  registering handlers with the engine object. The engine object can be
found by importing the __main__ namespace, at __main__._engine

Engine structure:
-----------------
Engine(MessageBus Node)              
    Compiler        -   Handles the compilation of python code and display of errors.
    Debugger        -   debugger traceback object.
    Profiler        -   profiler function object.

Connection:
-----------
After creating the Engine object, connect/listen is called to register with a 
MessageBus with a unique nodename/engine id of the form 'Engine.'. followed by 
the unique process ID.
 
A Console should be created to control the Engine, This is another MessageBus
local node. It will start managing the engine when it's Console.SetEngine() 
method is called.

PTK:
----
Once a connection to the MessageBus has been established  a SYS_NODE_CONNECT 
will be published. The console tool subscribes to SYS_NODE_CONNECT messages 
and on recieving this it will create a Console object to control the engine.

"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

#---imports---------------------------------------------------------------------
from codeop import _maybe_compile, Compile
from code import softspace
import sys
import os
import __main__
import __builtin__                      #for adding builtin commands
import marshal                          #for task/builtins
import types                            #for task/builtins
from threading import Event             #for readline events
import thread                           #to interupt, running code.

from ptk_lib.message_bus import mb_protocol
from ptk_lib.message_bus.mb_client import MBClient

from eng_compiler import EngineCompiler
from eng_debugger import EngineDebugger
from eng_profiler import EngineProfiler
import eng_messages                     #standard engine message types
import eng_tasks                        #engine task utils  

#-------------------------------------------------------------------------------
# pseudo file object used to redirect stdio
#-------------------------------------------------------------------------------
class PseudoFile:
    def __init__(self,readline=None,readlines=None,write=None):
        """Create a file-like object."""
        #setup inputs:
        if readline is not None:
            self.readline  = readline
        if readlines is not None:
            self.readlines = readlines
        #setup output:
        if write is not None:
            self.write = write

    def readline(self):
        pass
    def write(self, s):
        pass
    def writelines(self, l):
        map(self.write, l)
    def flush(self):
        pass
    def isatty(self):
        return 1

#-------------------------------------------------------------------------------
# The main engine class
#-------------------------------------------------------------------------------
class Engine(MBClient):
    engtype = 'Embedded.base'

    def __init__(self, englabel='New engine', userdict={}, timeout=10):
        """
        Base class/mixin implementation of an Engine, this should be used with a
        MessageBus node/client.

        englabel    -   The label that should be displayed to the user for the 
                        engine or none
        userdict    -   dictionary for the user namespace
        timeout     -   Timeout in seconds when connecting and waiting for 
                        message replies
        """
        #check if an engine already exists in this process
        if __main__.__dict__.has_key('_engine'):
            raise Exception('An engine already exists (as __main__.engine) in this process! reuse!')

        #get node name for this engine.
        node_name = 'Engine.'+str(os.getpid())

        #client init
        MBClient.__init__(self, node_name, timeout)

        #-----------------------------------------------------------------------
        # Attributes
        #-----------------------------------------------------------------------
        self.englabel = englabel    #engine label displayed to user.
        self.console = None         #controlling console node name
        
        #engine prompts are changable, these are what is shown in the console, 
        #so an engine may want to display it's name.
        self.prompts = ( '>>> ', '??? ')            

        #icon to display on console or None
        self.engicon = None         

        #flags
        self.busy     = False          #running a user command
        self.debug    = False          #use traceback debugger
        self.profile  = False          #use profiler

        #internal flags
        self._stop     = False         #used to catch stop running code exceptions
        self._stop_quiet  = False      #used to catch excecption and prevent 
                                       # prompt when exiting/disconnecting.

        #dictionary to execute user commands in.
        if userdict is None:
            userdict = __main__.__dict__
        self._userdict = userdict

        #store registered engine tasks {name:func}
        self._tasks = {}

        #-----------------------------------------------------------------------
        # Sub components
        #-----------------------------------------------------------------------

        #Compiler handles the compilation of code.
        self.compiler = EngineCompiler(self)

        #Debugger handles the exectution of code with the debugger enabled
        self.debugger = EngineDebugger(self)

        #Profiler handles the execution of code with the profiler enabled
        self.profiler = EngineProfiler(self)

        #-----------------------------------------------------------------------
        # Set up the working environment
        #-----------------------------------------------------------------------
        #the builtins module
        exec('import __builtin__ as __builtins__',self._userdict)
        
        #store the engine process object in the main namespace for use by 
        #extensions
        __main__._engine = self

        #register standard engine tasks
        self.register_task(eng_tasks.object_exists)
        self.register_task(eng_tasks.get_type_string)
        self.register_task(eng_tasks.execute_startup_script)
        self.register_task(eng_tasks.get_cwd)
        self.register_task(eng_tasks.set_cwd)

        #-----------------------------------------------------------------------
        # attributes for redirecting standard input/output
        #-----------------------------------------------------------------------
        #attributes for reading from stdin
        self._isreading = False     #flag indicating we are waiting for input.
        self._readend = ''          #string that indicates enough.
        self._readresult = ''       #read input goes here for collection.
        self._readevent = Event()   #event to wake readline

        #this redirects all sys.std* io to the gui process
        self._stdin  = PseudoFile(readline=self.readline, readlines=self.readlines)
        self._stdout = PseudoFile(write=self.write_stdout)
        self._stderr = PseudoFile(write=self.write_stderr)

        self._old_stdin = sys.__stdin__
        self._old_stdout = sys.__stdout__
        self._old_stderr = sys.__stderr__

        #-----------------------------------------------------------------------
        #Set up the interface/engine communications
        #   - compiler/debugger/profiler also register message handlers
        #-----------------------------------------------------------------------  
        self.set_handler(eng_messages.ENG_MANAGE, self.msg_manage)
        self.set_handler(eng_messages.ENG_RELEASE, self.msg_release)

        self.set_handler(eng_messages.ENG_PUSH, self.msg_push)
        self.set_handler(eng_messages.ENG_STOP, self.msg_stop)

        self.set_handler(eng_messages.ENG_DEBUG_TOGGLE,  self.msg_toggle_debug)
        self.set_handler(eng_messages.ENG_PROFILE_TOGGLE, self.msg_toggle_profile)

        self.set_handler(eng_messages.ENG_EXECCOMMAND, self.msg_exec)
        self.set_handler(eng_messages.ENG_EVALCOMMAND, self.msg_eval)
        self.set_handler(eng_messages.ENG_RUNTASK, self.msg_run_task)
        self.set_handler(eng_messages.ENG_REGISTERTASK, self.msg_register_task)
        self.set_handler(eng_messages.ENG_ADDBUILTIN, self.msg_add_builtin)
        self.set_handler(eng_messages.ENG_GETTASKS, self.msg_get_tasks)

    #---------------------------------------------------------------------------
    # Connection/Disconnection
    #---------------------------------------------------------------------------
    #connect/disconnect (to MessageBus) - implemented by the MessageBus Node or 
    #client.
    #When the engine node disconnects this will be called (i.e. to close an 
    # engine the controlling process can disconnect the messagebus connection).
    #If the managing console disconnects the engine will wait for a new 
    #manageing console.
    def manage(self, console):
        """
        Allow a console to manage this engine.
        """
        #already being managed
        if self.console is not None:
            return False

        #set the console node for communications
        self.console = console

        #subscribe to console node sys messages
        self.subscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+self.console, 
                        self.msg_node_disconnect)

        #redirect stdIO
        self.redirect_stdio()

        #print a welcome message and prompt for input
        self.write_stdout( self.get_welcome())
        self.send_msg(self.console, eng_messages.CON_PROMPT,
                            (self.prompts[0],False))

        #and return a result dictionary
        #{type, name/label, icon, pid} etc
        info =  {'engtype': self.engtype, 
                 'englabel': self.englabel,
                 'engicon': self.engicon,
                 'pid': os.getpid()}
        return info

    def release(self):
        """
        Release the engine from a console's control
        """
        #not being managed - release anyway.
        if self.console is None:
            return True

        #unsubscribe from the releasing console node sys messages
        self.unsubscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+self.console, 
                        self.msg_node_disconnect)

        #set console to None
        self.console = None

        #restore stdio
        self.restore_stdio()

        return True

    def exit(self):
        """
        Called when the a System exit is raised in running code
        """
        #call the node/client disconnect method to close the node properly.
        self.disconnect()

    def on_disconnect(self):
        """
        Overloaded on_disconnect method of client to preform engine tasks
        """
        MBClient.on_disconnect(self)

        #make sure engine is released and stdio streams restored
        self.release()

        #Could stop any running user code here but for remote engines the user 
        #may want to disconnect and leave it running and connect again later. 
        #self.stop_code(quiet=True)

    def on_err_disconnect(self):
        """
        Overloaded on_err_disconnect method to call both base classes
        """
        MBClient.on_err_disconnect(self)
        #make sure engine is released and stdio streams restored
        self.release()

        #Could stop any running user code here but for remote engines the user 
        #may want to disconnect and leave it running and connect again later. 
        #self.stop_code(quiet=True)

    #---------------------------------------------------------------------------
    # Interface methods
    #---------------------------------------------------------------------------
    def push_line(self, line):
        """A new line of user input"""
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        ##line is user command compile it
        ismore,code,err = self.compiler.compile(line)

        #need more 
        #   - tell the console to prompt for more 
        if ismore:
            self.send_msg( self.console, eng_messages.CON_PROMPT,
                            (None, True) )
            return

        #syntax error
        #   - compiler will output the error
        #   - tell the console to prompt for new command 
        if err:
            self.send_msg(self.console, eng_messages.CON_PROMPT,
                            (self.prompts[0],False))
            return

        #no code object - could be a blank line
        if code is None:
            self.send_msg(self.console, eng_messages.CON_PROMPT,
                            (self.prompts[0],False))
            return

        ##have some code to execute so call run_code to do something with it
        self.run_code(code)

    def _run_code(self, code):
        """
        Run the code object in the engine - THIS SHOULD NOT BE CALLED DIRECTLY
        USE run_code() which is thread safe.
        """
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        #set busy flag and send busy messages
        self.busy = True
        
        #published message
        self.publish_msg(   eng_messages.ENGINE_STATE_BUSY+'.'+self.name, 
                            data=(self.debug, self.profile) )
     
        #enable debugger?
        if self.debug is True:
            trace_func = self.debugger
        else:
            trace_func = None

        #enable profiler?
        if self.profile is True:
            profile_func = self.profiler
        else:
            profile_func = None

        #run the code
        try:
            sys.settrace(trace_func)
            sys.setprofile(profile_func)
            exec code in self._userdict
            sys.settrace(None)
            sys.setprofile(None)

        #system exit  - call engine.exit()
        except SystemExit:
            sys.settrace(None)
            sys.setprofile(None)
            self.busy = False
            log.debug('system exit in runnning code')
            self.exit()
            return

        #keyboard interrupt stopped running code
        except KeyboardInterrupt:
            sys.settrace(None)
            sys.setprofile(None)
            self.busy = False

            #engine stopped code in order to exit/or disconnect - do not prompt.
            if self._stop_quiet:
                self._stop_quiet = False
                return

            #user stopped code
            self._stop = False
            if self._isreading: #cancel the read prompt.
                self.send_msg( self.console, eng_messages.CON_PROMPT_STDIN, 
                                data=(self.prompts[1],None,))
            sys.stderr.write('STOP: User forced running code to stop.\n\n')
        
        #other exception - could be an error 1) caused by the engine exiting 2) a different error caused by
        #the KeyboardInterrupt (wxpython doesn't play nice!) or 3) a user code error
        except:
            sys.settrace(None)
            sys.setprofile(None)
            self.busy = False

            #1) engine is exiting/stopping quietly -  probably some error 
            # caused by engine exiting
            if self._stop_quiet:
                self._stop_quiet = False
                log.exception('Exception raised to stop running code? - engine wants to exit.')
                return

            #2) user stopped code
            if self._stop is True:
                self._stop = False
                if self._isreading: #cancel the read prompt.
                    self.send_msg( self.console, eng_messages.CON_PROMPT_STDIN,
                                     data=(self.prompts[1], None,))
                sys.stderr.write('STOP: User forced running code to stop.\n\n')

            #3) error in user code.
            self.compiler.show_traceback()

        #reset internal state flags
        self.busy = False
        self._isreading = False
        if self.debug is True:
            self.debugger.reset()

        #softspace makes the print statement work correctly when using final 
        #comma to supress newlines.
        if softspace(sys.stdout, 0):
            print 

        #If exiting skip the rest.
        if self._stop_quiet is True:
            return

        #send an engine done message
        self.publish_msg(   eng_messages.ENGINE_STATE_DONE+'.'+self.name, 
                            data=(self.debug, self.profile) )
     
        #prompt the console for new command
        try:
            self.send_msg(self.console, eng_messages.CON_PROMPT,
                            (self.prompts[0], False,))
        except:
            log.exception('error ')
            pass

    def stop_code(self, quiet=False):
        """
        Attempt to stop the running code by raising a keyboard interrupt in
        the main thread.

        If the optional quiet flag is True the engine will stop the code but not
        print an error message or prompt again.
        """
        if self.busy is False:
            return

        #set the stop flag to catch the error correctly
        if quiet:
            self._stop_quiet = True
        else:
            self._stop = True

        #make sure we are not stuck in readline(s) 
        if self._isreading:
            self._readevent.set()

        #make sure the debugger is not paused.
        if self.debug is True:
            self.debugger.stop_code()
            return

        #try a keyboard interrupt - this will not work for the internal engine 
        # as the error is raised here instead of the running code, hence put in 
        #try clause.
        try:
            thread.interrupt_main()
        except:
            pass

    def evaluate(self,expression):
        """
        Evaluate expression in engine and return result (like builtin eval)
        
        It is intened to be used to provide functionality to the GUI, so commands
        should be fairly quick to process to avoid blocking.
        
        Returns None on errors
        """
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        globals = self._userdict
        locals = self._userdict

        #try to evaluate the expression
        try:
            result = eval(expression, globals, locals)
        except:
            result = None
        return result

    def execute(self,expression):
        """
        Execute expression in engine (like builtin exec)

        It is intened to be used to provide functionality to the GUI interface,
        so commands should be fairly quick to process to avoid blocking the 
        communications thread.
        """
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        globals = self._userdict
        locals = self._userdict

        #execute the expression
        try:
            exec(expression, globals, locals)
        except:
            pass

    def run_task(self,taskname, args=(), kwargs={}):
        """
        Run a complex task in the engine; taskname is the name of a registered 
        task function taking the following arguments: 
                task(globals, locals, *args, **kwargs)
        """        
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        #get the task
        task = self.get_task(taskname)

        globals = self._userdict
        locals = self._userdict
                
        #run the task
        try:
            result=task(globals, locals, *args, **kwargs)
        except:
            log.exception('run_task failed :'+task.func_name)
            raise

        return result

    def register_task(self,task):
        """
        Register a task with the process.
        """
        log.debug('Registering task '+task.func_name)
        if self._tasks.has_key(task.func_name):
            result = False
        else:
            self._tasks[task.func_name]=task
            result=True
        return result

    def get_task(self, taskname):
        """
        Get a registered task callable.
        """
        #get the task
        if self._tasks.has_key(taskname) is False:
           raise NameError('No task with name: '+taskname)
           
        task = self._tasks[taskname]
        return task

    def enable_debug(self,flag=True):
        """ Enable the debugger - returns debug state """

        #already set to the correct state
        if flag == self.debug:
           return self.debug

        #engine is busy
        if (self.busy is True):
            #cannot enable/disable debugging when running a command.
            return self.debug

        #engine is inactive set to flag
        self.debug = flag

        #publish debug toggle message
        data = (self.debug,)
        self.publish_msg(eng_messages.ENGINE_DEBUG_TOGGLED, data)  

        return self.debug

    def enable_profile(self, flag=True):
        """ Enable the profiler - returns profiler state """
        #cannot enable/disable profiler if running a command.
        if self.busy is True:
            return self.profile

        #enable profiler/disable debugger
        self.profile = flag    

        #publish debug toggle message
        data = (self.profile,)
        self.publish_msg(messages.ENGINE_PROFILE_TOGGLED, data)  

        return self.profile

    def notify_change(self):
        """
        Publish an engine state change message to notify that the engine state 
        may have changed. For example after running an engine task or exec 
        command that modifies engine objects.
        """
        data = (self.busy, self.debug, self.profile)
        self.publish_msg( eng_messages.ENGINE_STATECHANGE+'.'+self.name, data)

    #---------------------------------------------------------------------------
    # standard IO methods
    #---------------------------------------------------------------------------
    def readline(self):
        """std in readline directs here- this calls the stdin handler for input"""
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        #set flag
        self._isreading = True
        self._readend = '\n'  #string to indicate enough
        self._readresult = ''
        self._readevent.clear()

        #request input from the interface
        self.send_msg(self.console, eng_messages.CON_PROMPT_STDIN,
                        (self.prompts[1], False,))

        #wait until _readevent is set
        self._readevent.wait()
        self._isreading = False

        #reset the event for next read
        self._readevent.clear()
        #reset the read result buffer
        result = self._readresult
        self._readresult = ''
        return result

    def readlines(self):
        """std in readlines directs here"""
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        #set flag
        self._isreading = True
        self._readend = '\n\n' #string to indicate enough
        self._readresult = ''
        self._readevent.clear()

        #request input from the interface
        self.send_msg(self.console, eng_messages.CON_PROMPT_STDIN,
                        (self.prompts[1],False))

        #wait until _readevent is set
        self._readevent.wait()
        self._isreading = False

        #reset the event for next read
        self._readevent.clear()
        #reset the read result buffer
        result = self._readresult
        self._readresult = ''
        return result

    def push_stdin(self, line):
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')

        #check if we have enough input
        if line.endswith(self._readend):
            #store here to be collected in readline(s)
            self._readresult = line 
            #wake readline
            self._readevent.set()
			
        else:
            self.send_msg(self.console, eng_messages.CON_PROMPT_STDIN,
                            (None,True))

    def write_stdout(self,string):
        """std out write redirects here"""
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')
        #sys.__stdout__.write(string)
        try:
            self.send_msg(self.console, eng_messages.CON_WRITE_STDOUT,(string,))        
        except:
            pass        

    def write_stderr(self,string):
        """std err write redirects here"""
        #check for a console
        if self.console is None:
            log.warning('No managing console!')
            raise Exception('No managing console!')
        #sys.__stderr__.write(string)
        try:
            self.send_msg(self.console, eng_messages.CON_WRITE_STDERR,(string,))
        except:
            pass        

    def redirect_stdio(self):
        """
        Redirect stdIO streams to PTK console
        """
        if sys.stdin != self._stdin:
            #store existing stdin in case already redirected
            self._old_stdin = sys.stdin
            #use our redirection object
            sys.stdin   = self._stdin

        if sys.stdout != self._stdout:
            #store existing stdout in case already redirected
            self._old_stdout = sys.stdout
            #use our redirection object
            sys.stdout  = self._stdout
        
        if sys.stderr != self._stderr:
            #store existing stderr in case already redirected
            self._old_stderr = sys.stderr
            #use our redirection object
            sys.stderr  = self._stderr

    def restore_stdio(self):
        """
        Restore the stdIO streams
        """
        #restore stdIO
        sys.stdin   = self._old_stdin
        sys.stdout  = self._old_stdout
        sys.stderr  = self._old_stderr

    #---------------------------------------------------------------------------
    # Other methods to implement in subclasses
    #---------------------------------------------------------------------------
    def run_code(self,code):
        """
        Run some compiled code as the user.

        Typically this needs to be run in the main thread - not the comms thread
        which calls this method, so an event of some sort should be raised here 
        to wake the main thread which can then call run_code
        """ 
        pass

    def get_welcome(self):
        """Return the standard part of engines welcome message"""
        ver = sys.version
        plat = sys.platform
        info = "Type \"help\", \"copyright\", \"credits\" or \"license\" for more information.\n"
        welcome = ( "Python "+ver+" on "+plat+" \n"+info)
        return welcome
    #---------------------------------------------------------------------------
    # message handlers
    #---------------------------------------------------------------------------
    def msg_manage(self, msg):
        """
        Sent by the Console assigned to control this engine. The engine is then 
        ready to operate until it is disconnected or released by the console.
        """
        console = msg.get_from()
        return self.manage(console)

    def msg_release(self, msg):
        """
        Sent by the managing console to release the engine. It should then be
        inactive until a new console takes management.
        """
        return self.release()

    def msg_node_disconnect(self, msg):
        """
        A node disconnected, check if it was the console.
        """
        name, err = msg.get_data()
        if name == self.console:
            #node was controlling console
            self.release(self.console)

    def msg_push(self, msg):
        """Process a line from the console"""
        line, = msg.get_data()
        ##data is a line of input
        if self._isreading:
            #log.debug('stdin data received '+str(line))
            self.push_stdin(line)
            type = 'STD_IN'

        ##debugger is active and we are running a command
        elif self.debug and self.busy:
            #log.debug('debugger cmd received '+str(line))
            self.debugger.push_line(line)
            type = 'DBG_CMD'
        
        ##a user command
        else:
            #log.debug('user command received '+str(line))
            self.push_line(line)
            type = 'CMD'
           
        #publish a message that a complete line was processed for the command 
        #history
        data = (line, type)
        self.publish_msg( eng_messages.ENG_LINE_PROCESSED, data)

    def msg_toggle_debug(self, msg):
        """Enable the debugger traceback"""
        res = self.enable_debug(msg.data[0])
        return res

    def msg_toggle_profile(self, msg):
        """Enable the profiler"""
        res = self.enable_profile(msg.data[0])
        return res

    def msg_stop(self, msg):
        self.stop_code()

    def msg_exec(self, msg):
        """Execute expression"""
        #data can have optional level argument for use with debugger
        if len(msg.data)==2:
            expression, level = msg.data
        else:
            expression, = msg.data
            level = None

        #if debugging use the debugger interfaces
        if self.debug and self.busy:
            self.debugger.execute(expression, level)
        else:
            self.execute(expression)

    def msg_eval(self, msg):
        """Evaluate expression and return result"""
        #data can have optional level argument for use with debugger
        if len(msg.data)==2:
            expression, level = msg.data
        else:
            expression, = msg.data
            level = None

        #if debugging use the debugger interfaces
        try:
            if self.debug and self.busy:
                result = self.debugger.evaluate(expression, level)
            else:
                result = self.evaluate(expression)
        except Exception as e:
            return e
        return result

    def msg_run_task(self, msg):
        """Run an pre-registered engine task and return the result"""
        #data is a task name, args, kwargs plus optional level argument for use 
        #with debugger
        if len(msg.data)==4:
            taskname,args,kwargs,level = msg.data
        else:
            taskname,args,kwargs = msg.data
            level = None

        #if debugging use the debugger interfaces
        try:
            if self.debug and self.busy:
                result = self.debugger.run_task(taskname, args, kwargs, level)
            else:
                result = self.run_task(taskname, args, kwargs)
        except Exception as e:
            return e
        return result

    def msg_register_task(self, msg):
        """Register a new task with the engine"""
        #data is name and marshalled code object
        s = msg.data[0]
        c = marshal.loads(s)
        task = types.FunctionType(c,{'__builtins__':__builtins__},None)
        result = self.register_task(task)
        return result

    def msg_get_tasks(self, msg):
        """Return the registered task names"""
        return self._tasks.keys()

    def msg_add_builtin(self, msg):
        """add a command to the builtins module"""
        name, s = msg.get_data()
        code = marshal.loads(s)
        cmd = types.FunctionType(code,{'__builtins__':__builtins__},None)
        __builtin__.__dict__[name] = cmd
        return True
    
#-------------------------------------------------------------------------------
# PTK engine mixin class - adds remote engine functionaility via a 2nd MsgChannel
#-------------------------------------------------------------------------------
# Engine connected as normal:
#
# Whene enable_remote/disable_remote message recieved
#   - Creates remote MsgChannel and starts listening 
#
# When remote PTK connects:
#   - locks parent PTK instance print message,console: isinteractive > False
#   - sets remote_active flag
#   engine.connected returns the remote_channel connected flag
#   engine.name returns the remote_channels connected flag
#

# If disable_Remote message recieved:
#     -stop listening
#     -disconnect from connected remote PTK.
#     - return control to the parent PTK instance 
#           remote_active = False
#           if reading send PROMPT_STDIN
#           send ENGINE_STATE_CHANGE to refresh tools.
#
# if remote PTK connects:
#       -register with the remote PTK instance (name maybe different so engine.name
#        needs to be a dynamic attribute which uses the node name of the parent 
#        msg_channel or remote msg_channel depending upon the state.
#
#        manage() is overloaded to
#
#
#class PTKEngine_mixin():
#    def __init__(self):
#
#        #flag to indicate engine is listening for or in remote mode.
#        self.remote_enabled = False
#
#        #MsgChannel connected to the remote PTK instance
#        self._remote_channel = None
#
#        #Console name used by the remote PTK instance
#        self.remote_console = None
#
#        self.set_handler(eng_messages.ENG_REMOTE_TOGGLE, self.msg_remote_toggle)
#    #---------------------------------------------------------------------------
#    @property   
#    def is_remote(self):
#        if self.remote_enabled and self._remote_channel.connected:
#            return True
#        else:
#            return False
#
#    @property
#    def name(self):
#        #use parent PTK node name
#        if self.remote_enabled is False:
#            if self._channel is None:
#                return self._name
#            else:
#                return self._channel.name
#
#        #use remote PTK node name
#        else:
#            if self._remote_channel is None:
#                return self._name
#            else:
#                return self._remote_channel.name
#
#    @property
#    def console(self):
#        if self.remote_enabled:
#            return self.remote_console
#        else:
#            return self.__dict__['console']
#
#    #---------------------------------------------------------------------------
#    def manage(self, console):
#        if self.remote_enabled:
#	    pass
#        #store console name as _remote_console
#        #set remote flag in info dictionary
#
#    def _manage_remote(self, console):
#        """
#        Allow a console to remotely manage this engine.
#        """
#        #already being managed
#        if self._remote_console is not None:
#            return False
#
#        #set the console node for communications
#        self._remote_console = console
#
#        #subscribe to console node sys messages
#        self.subscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+self.console, 
#                        self.msg_node_disconnect)
#
#        #redirect stdIO
#        self.redirect_stdio()
#
#        #print a welcome message and prompt for input
#        self.write_stdout( self.get_welcome())
#        self.send_msg(self.console, eng_messages.CON_PROMPT,
#                            (self.prompts[0],False))
#
#        #and return a result dictionary
#        #{type, name/label, icon, pid} etc
#        info =  {'engtype': self.engtype, 
#                 'englabel': self.englabel,
#                 'engicon': self.engicon,
#                 'pid': os.getpid()}
#        return info
#
#    def release():
#        pass
#        #if self.remote_
#    def enable_remote(self):
#        pass
#
#    def disable_remote(self):
#        pass
#
#    def send_msg():
#        #send via correct msg_channel depending upon state.
#        pass
#
#    def publish_msg():
#        pass
#
#    def msg_remote_toggle(self, msg):
#        #create a remote channel
#        pass
#