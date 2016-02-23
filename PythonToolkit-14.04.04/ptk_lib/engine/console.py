"""
console.py 
--------------

Console - is the control interface to engines it is a MBLocalNode subclass
connected to the same messagebus as the engine it is to control.

A console class should subclass this and implement the console methods prompt, 
read_stdin etc to define what to do when communicating with the engine.

The console also provides the interface to determine the engines state and to 
control the engine and debugger/profiler.
"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

import marshal
import os
import signal

from ptk_lib.message_bus.mb_node import MBLocalNode
from ptk_lib.message_bus import mb_protocol

import eng_messages

#---Console class---------------------------------------------------------------
class Console(MBLocalNode):
    def __init__(self, msg_bus, node_name='Console.*'):
    
        #MBLocal initialisation
        MBLocalNode.__init__(self, node_name)
        self.connect(msg_bus)

        #other engine attributes set in set_managed_engine()
        self.engine = None              #engine node name to control
        self.is_interactive = False     #engine is connected and being managed
        self.engtype = None             #engine type
        self.engicon = None             #engine icon
        self.englabel = None            #engine label
        self.engpid = None              #engine process id

        #flags to keep track of engine state
        self.busy      = False          #engine is running a command
        self.debug     = False          #engine debugger is enabled
        self.profile   = False          #engine profiler is enabled
        self.reading   = False          #engine is waiting to read from stdin
        self.debugging = False          #engine is in debugging mode.

        #debugger interface
        self.debugger = DebuggerInterface(self)

        #profiler interface
        #TODO

        #-----------------------------------------------------------------------
        #set handlers for messages
        #-----------------------------------------------------------------------
        #prompt messages
        self.set_handler( eng_messages.CON_PROMPT, self.msg_prompt)
        self.set_handler( eng_messages.CON_PROMPT_STDIN, self.msg_prompt_stdin)
        self.set_handler( eng_messages.CON_PROMPT_DEBUG, self.msg_prompt_debug)

        #output messages
        self.set_handler( eng_messages.CON_WRITE_STDOUT, self.msg_write_stdout)
        self.set_handler( eng_messages.CON_WRITE_STDERR, self.msg_write_stderr)
        self.set_handler( eng_messages.CON_WRITE_DEBUG,  self.msg_write_debug)

        #others
        self.set_handler( eng_messages.CON_CLEAR, self.msg_console_clear)
        self.set_handler( eng_messages.CON_EXECSOURCE, self.msg_execsource)

    #---engine-console interactions---------------------------------------------
    def set_managed_engine(self, engnode):
        """
        Set the engine node that the console should manage.
        When it connects the console will take control.
        When it disconnects the console will prevent interaction (via the 
        is_interactive flag).
        """
        #check if already managing an engine
        if self.is_interactive is True:
            raise Exception('Already managing an engine node - call release_engine')

        #unsubscribe from previous engine messages
        if self.engine is not None:
            #system messages
            self.unsubscribe( mb_protocol.SYS_NODE_CONNECT+'.'+self.engine,
                                self.msg_node_connect )
            self.unsubscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+self.engine, 
                                self.msg_node_disconnect)

            #busy/done
            self.unsubscribe( eng_messages.ENGINE_STATE_BUSY+'.'+self.engine,
                                self.msg_busy)
            self.unsubscribe( eng_messages.ENGINE_STATE_DONE+'.'+self.engine,
                                self.msg_done)

        #subscribe to new engines messages
        #system messages
        self.subscribe( mb_protocol.SYS_NODE_CONNECT+'.'+engnode,
                        self.msg_node_connect )
        self.subscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+engnode, 
                        self.msg_node_disconnect)

        #busy/done
        self.subscribe( eng_messages.ENGINE_STATE_BUSY+'.'+engnode, self.msg_busy)
        self.subscribe( eng_messages.ENGINE_STATE_DONE+'.'+engnode, self.msg_done)

        #do debugger/profiler set_managed_engine
        self.debugger._set_managed_engine(engnode)
        #self.profiler._set_managed_engine(engnode)

        #store the new engines node name and set the default label
        self.engine = engnode
        self.englabel = engnode

        #if the engine is already connected to the message bus start managing it
        if self.msgbus.has_node(self.engine):
            self.manage()

    def manage(self):
        """
        Start controlling the engine. Returns sucess flag.
        """
        #check if already managing the engine
        if self.is_interactive is True:
            return False

        #send message to take control
        info = self.send_msg(self.engine, eng_messages.ENG_MANAGE,
                             (), get_result=True)

        #unsuccessfull attempt to manage engine (another console is managing?)
        if info is False:
            return False
        
         #set the is_interactive flag to indicate the console can do things.
        self.is_interactive = True 

        #store engine attributes (type, icon and label)
        self.engtype = info['engtype']
        self.engicon = info['engicon']
        self.englabel = info['englabel']
        if self.englabel is None:
            self.englabel = self.engine
        self.engpid = info['pid']

        return True

    def release(self):
        """
        Stop managing the current engine node.
        The console will be inactive until an new engine node is set as managed.
        Returns True/False is success.
        """
        #not currently managing an engine
        if self.is_interactive is False:
            return True

        #cancel any prompts.
        self.prompt(None, None) 
        self.prompt_stdin(None, None)
        self.prompt_debug(None, None)

        #write an error
        self.write_stderr('\nStopped managing engine\n')

        #send the release message to the engine
        res = self.send_msg(self.engine, eng_messages.ENG_RELEASE,
                             (), get_result=True)
        if res is False:
            return False    #should not happen?

        #unsubscribe from previous engine messages
        if self.engine is not None:
            #system messages
            self.unsubscribe( mb_protocol.SYS_NODE_CONNECT+'.'+self.engine,
                                self.msg_node_connect )
            self.unsubscribe( mb_protocol.SYS_NODE_DISCONNECT+'.'+self.engine, 
                                self.msg_node_disconnect)

            #busy/done
            self.unsubscribe( eng_messages.ENGINE_STATE_BUSY+'.'+self.engine,
                                self.msg_busy)
            self.unsubscribe( eng_messages.ENGINE_STATE_DONE+'.'+self.engine,
                                self.msg_done)
                     
        self.engine = None           
        self.is_interactive = False #interactive flag
        self.engtype = None         #engine type
        self.engicon = None         #engine icon
        self.englabel = None        #engine label
        self.engpid = None          #engine pid
        
        return True

    #---engine control----------------------------------------------------------
    def push(self, line):
        """
        Push a line of user command to the engine.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        self.busy=True #assume busy until prompted

        #store the line - it will be added to the command history when the 
        # engine prompts for a new command - not a continuation
        self._previous = line
        #send the line to the engine
        self.send_msg( self.engine, eng_messages.ENG_PUSH, (line,))

    def register_task( self, task):
        """
        Register a complex task with the engine.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        s = marshal.dumps(task.func_code)
        res = self.send_msg( self.engine, eng_messages.ENG_REGISTERTASK,
                                        (s,), get_result=True)
        return res

    def run_task(self, taskname, args=(),kwargs={}, scope=None):
        """
        Run a complex task in the engine (must have been previously registered 
        using register_task).
        If the debugger is active and an integer scope is given the code will
        be exectuted in the scope at that level (scope=0 is the users namespace 
        dictionary), if scope is None the code will be executed in the user 
        namespace.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg( self.engine, eng_messages.ENG_RUNTASK, 
                                (taskname,args,kwargs,scope), get_result=True)

        if isinstance(res, Exception):
            raise res

        return res

    def execute(self, source, scope=None):
        """
        Execute source in the engine. 
        If the debugger is active and an integer scope is given the code will
        be exectuted in the scope at that level (scope=0 is the users namespace 
        dictionary), if scope is None the code will be executed in the user 
        namespace.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg( self.engine, eng_messages.ENG_EXECCOMMAND, 
                                    (source,scope), get_result=True)
        return res

    def evaluate(self, source, scope=None):
        """
        Evaluate source in the engine.
        If the debugger is active and an integer scope is given the code will
        be exectuted in the scope at that level (scope=0 is the users namespace 
        dictionary), if scope is None the code will be executed in the user 
        namespace.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg( self.engine, eng_messages.ENG_EVALCOMMAND, 
                                        (source,scope), get_result=True)
        if isinstance(res, Exception):
            raise res
        return res

    def add_builtin(self, func, name):
        """
        Add a function to the engines builtin module.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        s = marshal.dumps(func.func_code)
        res = self.send_msg( self.engine, eng_messages.ENG_ADDBUILTIN, 
                                    (name,s), get_result=True )
        return res

    def get_registered_tasks(self):
        """
        Returns a list of the registered engine task names.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg( self.engine, eng_messages.ENG_GETTASKS, (), 
                                        get_result=True)
        return res

    def is_task_registered(self, taskname):
        """
        Check if a task is registered
        """
        return taskname in self.get_registered_tasks()

    def notify_change(self):
        """
        Publish an engine state change message to notify that the engine state 
        may have changed. For example after running an engine task or exec 
        command that modifies engine objects.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        busy, debug, profile = self.get_state()
        data = (busy, debug, profile)
        self.publish_msg( eng_messages.ENGINE_STATE_CHANGE+'.'+self.engine, data)

    def set_compiler_flag(self, flag, setto=True):
        """
        Set or unset a __future__ compiler flag.
        """
        #TODO: remove this interface and convert to an engine task.
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg( self.engine, eng_messages.ENG_FUTUREFLAG, 
                                        (flag,setto), get_result=True)
        return res

    def stop(self):
        """
        Stop a running command.
        """
        if self.is_interactive is False:
            return False

        success = self.send_msg(self.engine, eng_messages.ENG_STOP, ())

    def kill(self):
        """
        Kill the engine process
        (If the engine is embedded this will kill the embedding application!)
        """
        if (self.engine == 'Engine:Internal') or (self.engpid==os.getpid()):
            raise Exception('Attempt to kill own process! - just quit')
        
        if self.engpid is None:
            raise Exception('Could not kill - no PID')
        
        #send kill signal
        os.kill(self.engpid, signal.SIGTERM )
        
        #make sure the engine message bus node get closed (sockets sometimes do
        #not disconnect until something tries to write!)
        self.msgbus.close_node(self.engine)
        
    def get_state(self):
        """
        Returns a tuple of engine state flags=(busy, debug, profile)
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        return (self.busy, self.debug, self.profile)

    def enable_debug(self, flag=True):
        """
        Enable the debugger.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg(self.engine, eng_messages.ENG_DEBUG_TOGGLE,
                            (flag,),True)
        #update state
        self.debug = res
        return res

    def enable_profile(self, flag=True):
        """
        Enable the profiler.
        """
        if self.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.send_msg(self.engine, eng_messages.ENG_PROFILE_TOGGLE,
                            (flag,), True)
        #update state
        self.profile = res

        return res

    #---console methods to implement in subclasses------------------------------
    def prompt(self, prompt, more=False):
        """
        Called when the engine prompts for more user commands, more is True if 
        the previously pushed line is imcomplete. more is None to disable the 
        prompt.
        """
        pass
        
    def prompt_stdin(self, prompt, more=False):
        """
        Called when the engine prompts for user input on std_in, 
        more is True if multiple lines are required or None to disable the
        reading prompt.
        """
        pass

    def prompt_debug(self, prompt, more=False):
        """
        Called when the debugger prompts for debugger commands.
        more=False then a new debugger prompt.
        more=True then it is a line continuation
        more=None to disable debugger prompt.
        """
        pass
    
    def write_stdout(self, string):
        """
        Called when the engine wants to write a string to the std_out.
        """
        pass

    def write_stderr(self, string):
        """
        Called when the engine wants to write a string to the std_err.
        """
        pass

    def write_debug(self, string):
        """
        Called when the engine wants to write a debugger message
        """
        pass

    def exec_source(self, source):
        """
        Add the source to the console and push it to the engine as if the user 
        typed the code.
        """
        pass

    def exec_file(self, filepath):
        """
        Execute the source as if entered at the console
        """
        pass

    def clear(self):
        """
        Clear the console
        """
        pass

    #---message handlers--------------------------------------------------------
    def msg_prompt(self, msg):
        prompt, more = msg.data
        self.prompt(prompt,more)

    def msg_prompt_stdin(self, msg):
        prompt,more = msg.data
        self.prompt_stdin(prompt,more)

    def msg_prompt_debug(self, msg):
        prompt,more = msg.data
        self.prompt_debug(prompt,more)

    def msg_write_stdout(self, msg):
        string = msg.data[0]
        self.write_stdout(string)

    def msg_write_stderr(self, msg):
        string = msg.data[0]
        self.write_stderr(string)

    def msg_write_debug(self, msg):
        string = msg.data[0]
        self.write_debug(string)

    def msg_console_clear(self, msg):
        self.clear()

    def msg_execsource(self, msg):
        source= msg.data[0]
        self.exec_source(source)
    
    def msg_busy(self, msg):
        """
        Handler for message from engine to console indicating the engine is busy
        """
        #update state
        self.busy = True
    
    def msg_done(self, msg):
        #update state
        self.busy = False

        #update the debugger interface state
        #flags
        self.debugger.paused = False
        self.debugger.can_stepin = False
        self.debugger.can_stepout = False
        #paused at
        self.debugger.scope_name = None
        self.debugger.filename = None
        self.debugger.lineno = None
        #scopes
        self.scopes = ['main']
        self.active_scope = 0

    def msg_node_connect(self, msg):
        """
        Called when the engine message bus node connects
        """
        self.manage()

    def msg_node_disconnect(self, msg):
        """
        Called when the engine message bus nodes disconnects
        """
        engname,err = msg.get_data()
        
        #cancel any prompts.
        self.prompt(None, None) 
        self.prompt_stdin(None, None)
        self.prompt_debug(None, None)

        #write an error
        if err is False:
            self.write_stderr('\nEngine disconnected\n')
        else:
            self.write_stderr('\nEngine disconnected unexpectedly\n')

        #set flags/attributes
        self.is_interactive = False #interactive flag

#---Debugger interface----------------------------------------------------------
class DebuggerInterface():
    def __init__(self, console):
        """
        Interface to the engine debugger (stored as console.debugger)
        """
        self.console = console              #parent console object

        #debugger state flags
        self.paused = False
        self.can_stepin = False
        self.can_stepout = False

        #scopes
        self.scopes = ['main']
        self.active_scope = 0

        #paused at
        self.scope_name = None
        self.filename = None
        self.lineno   = None
        
    #---engine-console interactions---------------------------------------------
    def _set_managed_engine(self, engnode):
        #unsubscribe from old engine's messages (if necessary)
        if self.console.engine is not None:
            self.console.unsubscribe( eng_messages.ENGINE_DEBUG_PAUSED +
                                    '.'+self.console.engine, 
                                    self.msg_debug_paused )
            self.console.unsubscribe( eng_messages.ENGINE_DEBUG_RESUMED +
                                    '.'+self.console.engine, 
                                    self.msg_debug_resumed)
            self.console.unsubscribe( eng_messages.ENGINE_DEBUG_SCOPECHANGED +
                                    '.'+self.console.engine, 
                                    self.msg_debug_scope)

        #subscribe to the new engine's messages
        self.console.subscribe( eng_messages.ENGINE_DEBUG_PAUSED +
                                    '.'+engnode, self.msg_debug_paused )
        self.console.subscribe( eng_messages.ENGINE_DEBUG_RESUMED +
                                    '.'+engnode, self.msg_debug_resumed)
        self.console.subscribe( eng_messages.ENGINE_DEBUG_SCOPECHANGED +
                                    '.'+engnode, self.msg_debug_scope)

    #---interfaces methods------------------------------------------------------
    def pause(self, flag=True):
        """
        Pause a running command.
        """
        if flag is False:
            return self.resume()

        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.console.send_msg( self.console.engine, 
                                    eng_messages.ENG_DEBUG_PAUSE, (),True)
        self.paused = res
        return res

    def resume(self):
        """
        Resume a running command.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.console.send_msg( self.console.engine, 
                                    eng_messages.ENG_DEBUG_RESUME, (),True)
        self.paused = not res
        return res

    def end(self):
        """
        End debugging and finish running command.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.console.send_msg( self.console.engine, 
                                    eng_messages.ENG_DEBUG_END, (),True)
        return res

    def step(self):
        """
        Step to the next line.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        self.console.send_msg( self.console.engine, 
                                eng_messages.ENG_DEBUG_STEP, ())

    def step_in(self):
        """
        Step into a new scope.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        self.console.send_msg(self.console.engine, 
                                eng_messages.ENG_DEBUG_STEPIN, ())

    def step_out(self):
        """
        Step out of a scope.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        self.console.send_msg(self.console.engine, 
                                eng_messages.ENG_DEBUG_STEPOUT, ())

    def set_active_scope(self, level):
        """
        Set the currently active scope for interogation
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        self.console.send_msg(  self.console.engine, 
                                eng_messages.ENG_DEBUG_SETSCOPE, (level,))

    def get_state(self):
        """
        Returns information on the debugger state.
        flags = (paused, can_stepin, can_stepout)
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        return (self.paused, self.can_stepin, self.can_stepout)

    def get_scopelist(self):
        """
        Returns the engine available scopes - only updated when paused!
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        return self.scopes

    def get_active_scope(self):
        """
        Returns the currently active scope being interogated - only valid when paused!
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        return self.active_scope

    def get_paused_at(self):
        """
        Returns the (scopename, filename, lineno) that the debugger is paused at.
        If not paused returns (None,None)
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        return self.scope_name, self.filename, self.lineno

    def set_breakpoint(self, bpdata):
        """
        Set a breakpoint.
        bpdata is a dictionary containing:
            id - a unique id for the breakpoint (used to clear/edit)

        And optionally:
            filepath - file to set breakpoint in
            lineno - lineno to set breakpoint at
            condition - tring to evaluate; result=True(break), False(skip)
            ignore_count - Number of times to skip the breakpoint.
            trigger_count - Number of times to trigger the breakpoint.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        if bpdata.has_key('id') is False:
            raise Exception('No breakpoint id key in bpdata')
        
        res = self.console.send_msg( self.console.engine, 
                    eng_messages.ENG_DEBUG_SETBP,(bpdata,), True )      
        return res   

    def clear_breakpoint(self, id):
        """
        Clear the debugger breakpoint with the id given.
        If id is None all breakpoints will be cleared.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.console.send_msg( self.console.engine, 
                    eng_messages.ENG_DEBUG_CLEARBP,(id,), True )
        return res

    def edit_breakpoint(self, id, **kwargs):
        """
        Edit a breakpoint.

        Only modify the keywords given (from filename, lineno, condition,
        trigger_count and ignore_count).

        e.g. edit_breakpoint( id=1, filename='test.py', lineno=23) will modify
        the breakpoint filename and lineno.
        """
        if self.console.is_interactive is False:
            raise Exception('Managed engine is not active')

        res = self.console.send_msg( self.console.engine, 
                                    eng_messages.ENG_DEBUG_EDITBP,
                                    (id, kwargs), True )
        return res

    #---message handlers--------------------------------------------------------
    def msg_debug_paused(self,msg):
        #update state
        paused_at, scope_list, active_scope, flags = msg.data

        #flags
        self.paused = True
        can_stepin, can_stepout = flags
        self.can_stepin = can_stepin
        self.can_stepout = can_stepout

        #paused at
        scope_name,filename, lineno = paused_at
        self.scope_name = scope_name
        self.filename = filename
        self.lineno = lineno

        #scopes
        self.scopes = scope_list
        self.active_scope = active_scope

    def msg_debug_resumed(self, msg):
        #update state
        #flags
        self.paused = False
        self.can_stepin = False
        self.can_stepout = False
        #paused at
        self.scope_name = None
        self.filename = None
        self.lineno = None
        #scopes
        self.scopes = ['main']
        self.active_scope = 0

    def msg_debug_scope(self, msg):
        #update state
        scopes, active_scope = msg.data
        self.scopes = scopes
        self.active_scope = active_scope

