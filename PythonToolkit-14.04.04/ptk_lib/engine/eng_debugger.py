"""
Engine debugger
---------------
- Handles all the debugger functions for the engine.
- Can set block files where tracing stops to prevent locks in communications thread
- Can set breakpoints to pause code.
- Can manually pause in traced code.

Messages, see eng_messages.py for details:

"""
#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

import inspect                          #for debugger frame inpsection
import sys                              #for set_trace etc
from threading import Event             #for events
import thread                           #for keyboard interrupt
import os.path                          #for absolute filename conversions
import ctypes                           #for pythonapi calls
    
from eng_misc import DictList           #dictlist class for storing breakpoint info
import eng_messages                         #standard engine message types

import traceback

help_msg = """
Debugger commands are entered as comments:

#help (#h) show this text.
#step (or #s) to step to the next line.
#stepin (or #si) to step into a new code block call.
#stepout (or #so) to step out of the current code block.
#resume (or #r) to resume running the code.
#setscope level (or #ss level) set the active scope, level is an integer scope level where 0 is the main user namespace.
#line (or #l) print the current line of source (if available).
#end (or #e) disable debugging and finsishing running the code - no further debugging can be performed.

These are case insensitive, e.g. #step, #Step, #STEP, #S and #s will all instruct the debugger to step to the next line.
"""

class EngineDebugger():
    def __init__(self, eng):
        self.eng = eng                  #parent engine
        self.prompt = 'DB> '

        #debugger state
        self._paused     = False #is paused.
        self._can_stepin = False #debugger is about to enter a new scope
        self._can_stepout= False #debugger can be stepped out of a scope

        #debugger command flags
        self._resume     = False #debugging was resumed.
        self._end        = False #stop debugging, finish running code
        self._stop       = False #stop running code
        self._stepin     = False #debugger step in to scope
        self._stepout    = False #debugger step out of scope

        #event used to wake the trace function when paused
        self._resume_event = Event()

        #user commands to execute when the debugger is paused
        #this is check in the trace function and executed in the active scope. 
        self._cmd = None

        #debugger scopes:
        #keep track of the different scopes available for tools to query
        self._scopes    = []        #list of scope (function) names
        self._frames    = []        #list of scope frames
        self._active_scope = 0 #the current scope level used for exec/eval/commands

        #internal variable used to keep track of where wer started debugging
        self._bottom_frame = None

        #files to look for when tracing...
        self._fncache = {}      #absolute filename cache
        self._block_files = []  #list of filepaths not to trace in (or any further)

        #prevent trace in all engine module files to avoid locks blocking comms threads.
        self.set_block_file( os.path.dirname(__file__)+os.sep+'*')

        #break points - info on breakpoints is stored in an MKeyDict instance
        # which allows items (the breakpoint data dict) to be retrieved by 
        # filename or id. The keys hcount, icount and tcount are breakpoint 
        # counters for hits, ignores and trigger counts and are reset before 
        # each user command.
        self.bpoints = DictList()
        self._bp_hcount = {} # hit counter {id: hcount}
        self._bp_tcount = {} # trigger counter {id: tcount}

        #Register message handlers for the debugger
        self.eng.set_handler(eng_messages.ENG_DEBUG_PAUSE, self.msg_debug_pause)
        self.eng.set_handler(eng_messages.ENG_DEBUG_RESUME, self.msg_debug_resume)
        self.eng.set_handler(eng_messages.ENG_DEBUG_END, self.msg_debug_end)
        self.eng.set_handler(eng_messages.ENG_DEBUG_STEP, self.msg_debug_step)
        self.eng.set_handler(eng_messages.ENG_DEBUG_STEPIN, self.msg_debug_stepinto)
        self.eng.set_handler(eng_messages.ENG_DEBUG_STEPOUT, self.msg_debug_stepout)
        self.eng.set_handler(eng_messages.ENG_DEBUG_SETSCOPE, self.msg_debug_setscope)
        self.eng.set_handler(eng_messages.ENG_DEBUG_SETBP, self.msg_dbg_setbp)
        self.eng.set_handler(eng_messages.ENG_DEBUG_CLEARBP, self.msg_dbg_clearbp)
        self.eng.set_handler(eng_messages.ENG_DEBUG_EDITBP, self.msg_dbg_editbp)

    #---------------------------------------------------------------------------
    # Interface methods
    #---------------------------------------------------------------------------
    def reset(self):
        """Reset the debugger internal state"""
        self._paused     = False 
        self._can_stepin = False 
        self._can_stepout= False 

        self._resume     = False 
        self._end        = False 
        self._stop       = False
        self._step_in    = False 
        self._step_out   = False 

        self._resume_event.clear()

        self._scopes = []
        self._frames = []
        self._active_scope = 0

        self._bottom_frame = None

        #resest breakpoint counters
        self._bp_hcount = {} # hit counter {id: hcount}
        self._bp_icount = {} # ignore counter {id: icount}
        self._bp_tcount = {} # trigger counter {id: tcount}

    def stop_code(self):
        """
        Attempt to stop the running code by raising a keyboard interrupt in
        the main thread
        """
        log.debug('Stopping code')
        self._stop = True       #stops the code if paused
        if self._paused is True:
            #turn console debug mode off -Note: None to turn off, True/False
            #is line continuation
            self.eng.send_msg( self.eng.console, 
                                eng_messages.CON_PROMPT_DEBUG, 
                                data=(self.prompt, None))
        
        self._resume_event.set()
        
        #try a keyboard interrupt - this will not work for the internal engine 
        # as the error is raised here instead of the running code, hence put in 
        #try clause.
        try:
            thread.interrupt_main()
        except:
            pass

    def end(self):
        """ End the debugging and finsish running the code """
        if self.eng.busy is False:
            return false

        #set the end flag and wake the traceback function
        #if necessary
        self._end=True  
        self._resume=True
        self._resume_event.set()
        return True

    def pause(self, flag=True):
        """ Pause currently running code - returns success """
        log.debug('Pausing code')
        if flag is False:
            return not self.resume()

        #already paused do nothing.
        if self._paused is True:
            return True

        #set the paused flag to pause at next oppertunity
        self._paused=True
        return True

    def resume(self):
        """ Unpause currently running code """
        #not paused - so cannot resume
        if self._paused is False:
            return False
        #set flag to false
        self._resume = True
        #set resume event to wake the traceback function
        self._resume_event.set()
        return True

    def step(self):
        """
        Step to the next line of code when the debugger is paused
        """
        #not paused - cannot step
        if self._paused is False:
            return False
        #make sure the step_in flag is False, so we don't step into a new scope
        #but rather step 'over' it.
        self._step_in = False
        #set the event so the trace function can resume - but don't change the 
        #paused flag so the code will pause again after the next line.
        self._resume_event.set()
        return True

    def step_in(self):
        """
        Step into the new scope (function/callable).
        This is only available if the next line is a 'call' event
        """
        #not paused or not at a call event
        if (self._paused is False) or (self._can_stepin) is False:
            return False

        #set the step in flag and wake the traceback function
        self._stepin = True 
        self._resume_event.set()
        return True

    def step_out(self):
        """
        Step out of a scope (function/callable).
        This is only available if the debugger is currently in a scope other
        than the main user namespace.
        """
        #check if we can step out
        if (self._paused is False) or (self._can_stepout is False):
            return False

        #set the step out flag and wake the traceback function
        #this will turn the traceback off for the current scope by returning 
        #None, as the new local trace function.
        self._can_stepout = False
        self._stepout = True
        self._resume_event.set()
        return True

    #breakpoints
    def set_breakpoint(self, bpdata):
        """
        Set a break point
        bpdata =  {id, filename, lineno, condition, ignore_count, trigger_count}
        where id should be a unique identifier for this breakpoint
        """
        #check if the id to use already exists.
        if len(self.bpoints.filter( ('id',),(id,)))!=0:
            log.warning('set breakpoint: id already exists')
            return False
            
        #check bpdata
        keys = bpdata.keys()
        if 'id' not in keys:
            log.warning('set breakpoint: bpdata does not have id key')
            return False
        elif 'filename' not in keys:
            log.warning('set breakpoint: bpdata does not have filename key')
            return False
        elif 'lineno' not in keys:
            log.warning('set breakpoint: bpdata does not have lineno key')
            return False
        elif 'condition' not in keys:
            bpdata['condition'] = None
        elif 'ignore_count' not in keys:
            bpdata['ignore_count'] = None
        elif 'trigger_count' not in keys:
            bpdata['trigger_count'] = None

        #create new breakpoint
        bpdata['filename'] = self._abs_filename( bpdata['filename'] )
        self.bpoints.append(bpdata)
        return True

    def clear_breakpoint(self, id):
        """
        Clear the debugger breakpoint with the id given.
        If id is None all breakpoints will be cleared.
        """
        if id is None:
            self.bpoints.clear()
            return True

        #check if the id to clear exists.
        bps = self.bpoints.filter( ('id',),(id,))
        if len(bps)==0:
            log.warning('clear breakpoint: id does not exist')
            return False

        #remove the breakpoint
        bp = bps[0]
        self.bpoints.remove( bp )
        return True

    def edit_breakpoint(self, id, **kwargs):
        """
        Edit a breakpoint.

        Only modify the keywords given (from filename, lineno, condition,
        trigger_count and ignore_count).

        e.g. edit_breakpoint( id=1, filename='test.py', lineno=23) will modify
        the breakpoint filename and lineno.
        """
        #check if the id to clear exists.
        bps = self.bpoints.filter( ('id',),(id,))
        if len(bps)==0:
            log.warning('modify breakpoint: id does not exist: '+str(id))
            return False

        bpdata= bps[0]
        if kwargs.has_key('filename'):
            kwargs['filename'] = self._abs_filename( kwargs['filename'] )
        bpdata.update(kwargs)
        return True

    #debugger command/interogration interface
    def get_scope(self, level=None):
        """
        Get the scope name,frame, globals and locals dictionaries for the scope at the
        level given (None=current scope, 0=user namespace dictionary).

        Note: To make any changes permanent you should call 
        _update_frame_locals(frame), with the frame.
        """
        #Note see http://utcc.utoronto.ca/~cks/space/blog/python/FLocalsAndTraceFunctions for possible problem!
        #Confirmed this issue - making a change to an existing variable will not
        #'stick' if the locals/globals are retreived again before the next line
        #is executed. 

        #To get round this either:
        #1)Keep a cache of the scopes globals/locals
        #to only fetch the dictionary once, after the next line the changes will
        #stick - but only to the top frame!
        #
        #2)Or using the python c api call that is called after the trace function
        #returns to make the changes stick immediately. This is done in the 
        #function  _update_frame_locals(frame)
        if level is None:
            level=self._active_scope
        if level>len(self._scopes) or level<0:
            raise Exception('Level out of range: '+str(level))
        #get the scope name
        name = self._scopes[level]
        frame = self._frames[level]
        globals = frame.f_globals
        locals = frame.f_locals
        return name,frame,globals,locals

    def set_scope(self, level):
        """
        Set the scope level to use for interogration when paused. This will be 
        reset at the next pause (i.e. after stepping).
        """
        #check level is an int
        if isinstance(level, int) is False:
            return False
        #check level is in range
        if level > (len(self._scopes)-1):
            return False
        #check if already in this level
        if level==self._active_scope:
            return True
        self._active_scope = level

        #print console message
        self.write_debug('Scope changed to: '+self._scopes[level]+
                              ' (level='+str(level)+')')
        #send scope change message
        data = (self._scopes, self._active_scope)
        self.eng.publish_msg(   eng_messages.ENGINE_DEBUG_SCOPECHANGED+'.'+
                                self.eng.name, data)

        return True

    def push_line(self,line):
        """
        A debugger commands to run - this is called from the engine when a 
        line is pushed and we are debugging and paused, so store internally and
        wake the debugger.
        """
        #not paused so not expecting any commands???
        if self._paused is False:
            log.warning('debugger command recieved when not paused!')
            return
        #have some code to execute so call run_user_command to do something with it
        #this wakes the resume event and runs the code in the mainthread
        self._cmd = line
        self._resume_event.set()

    #filepaths
    def set_block_file(self, filepath):
        """
        Set a filepath to block from tracing.
        use path* to include multiple files.
        """
        filepath = self._abs_filename(filepath)
        self._block_files.append(filepath)

    def get_block_files(self):
        """
        Get the filepaths that are currently blocked from tracing
        """
        return self._block_files

    #engine like interfaces
    def evaluate(self,expression, level=None):
        """
        Evaluate expression in the active debugger scope and return result 
        (like builtin eval)
        
        It is intened to be used to provide functionality to the GUI, so commands
        should be fairly quick to process to avoid blocking.

        The optional level argument controls the scope that will be used. 
        scope=None uses the current debugger scope and scope=0 is the top level 
        scope (the usernamespace).
        
        Returns None on errors
        """
        #get the scope locals/globals
        name,frame,globals,locals = self.get_scope(level)

        #try to evaluate the expression
        try:
            result = eval(expression, globals, locals)
        except:
            result = None

        #update the locals
        self._update_frame_locals(frame)
        return result

    def execute(self,expression, level=None):
        """
        Execute expression in engine (like builtin exec)

        It is intened to be used to provide functionality to the GUI interface,
        so commands should be fairly quick to process to avoid blocking the 
        communications thread.
        
        The optional level argument controls the scope that will be used. 
        scope=None uses the current debugger scope and scope=0 is the top level 
        scope (the usernamespace).
        """
        #get the scope locals/globals
        name,frame,globals,locals = self.get_scope(level)

        #execute the expression
        try:
            exec(expression, globals, locals)
        except:
            pass

        #update the locals
        self._update_frame_locals(frame)

    def run_task(self, taskname, args=(), kwargs={}, level=None):
        """
        Run a complex task in the engine; taskname is the name of a registered 
        task function taking the following arguments: 
                task(globals, locals, *args, **kwargs)
        
        The optional level argument controls the scope that will be used. 
        scope=None uses the current debugger scope and scope=0 is the top level 
        scope (the usernamespace).

        Returns None on errors.
        """
        #get the task
        task = self.eng.get_task(taskname)
        if task is None:
            raise NameError('No task with name: '+taskname)

        #get the scope locals/globals
        name,frame,globals,locals = self.get_scope(level)

        #run the task
        try:
            result=task(globals, locals, *args, **kwargs)
        except:
            log.exception('run_task failed :'+task.func_name)
            result=None

        #update the locals
        self._update_frame_locals(frame)

        return result

    #---------------------------------------------------------------------------
    # trace methods
    #---------------------------------------------------------------------------
    #Trace every line - why? 
    #1) It allows step out to work from a breakpoint in a nested scope
    #2) It makes the code easier to follow
    #3) It allows running code to be paused anywhere rather than just in traced scopes
    #The downside is speed, with every line now causing a call into python code
    def __call__(self, frame, event, arg):
        """ This trace function is called only once when debugging starts."""
        #store the first frame so we know where user code starts
        self._bottom_frame = frame
        #set the new global trace function
        sys.settrace(self._trace_global)

        #update the scope list
        self._update_scopes(frame)

        #return the local trace function for the first call
        return self._trace_global(frame, event, arg)

    def _trace_global(self, frame, event, arg):
        """The main trace function called on call events """
        ##---Prepause-----------------------------------------------------------
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt

        #check if the debugger want to end debugging.   
        if self._end is True:
            self.write_debug('Ending debugging')
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        name = frame.f_code.co_name
        lineno =  frame.f_lineno

        #if the file is on the block list do not trace
        #this is mainly engine/message bus files and prevents the user pausing and
        #locking the engine communications.
        if self._check_files(filename, self._block_files):
            return None
        #if the calling frame is also blocked return None
        if (frame.f_back.f_trace is None and frame!=self._bottom_frame):
            return None

        #if trace_stepout is the parent frames trace function then do not pause 
        #here unless there is a breakpoint set, just return the stepout trace function
        #which only checks for breakpoints and exits.
        elif (frame.f_back.f_trace) == (self._trace_stepout):
            return self._trace_stepout

        #check for breakpoints
        filename = self._abs_filename( filename )
        bps = self.bpoints.filter( ('filename','lineno'), (filename,lineno) )
        for bpdata in bps:
            self._paused = self._hit_bp( bpdata, frame)
            if self._paused is True:
                break
                
        #an exception!
        if event in ('exception','c_exception'):
            self._paused = True
            self._trace_pause(frame, event, arg)
            
        ##---Pause--------------------------------------------------------------
        #pause at this line?
        if self._paused is True:
            #This pauses until stepped/resumed
            self._trace_pause(frame, event, arg)
        
        ##---After pause--------------------------------------------------------
        #if paused and stepping in print a message
        if self._paused:
            if self._stepin is True:
                self.write_debug('Tracing in new scope: '+name)
                local_trace = self._trace_local
            else:
                #not stepping in so use the stepout function
                local_trace = self._trace_stepout
        #not paused so carry on with the normal trace function
        else:
            local_trace = self._trace_local

        #reset the can step in flags
        self._can_stepin = False 
        self._stepin = False

        return local_trace

    def _trace_local(self, frame, event, arg):
        """
        The local trace function
        - the main local trace function checks for breakpoints and pause requests
        - used for all traced scopes unless stepping out, or ending debugging.
        """
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt

        #check if the debugger want to end debugging.   
        if self._end is True:
            self.write_debug('Ending debugging')
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            #this is a python bug (as of python2.7 01/2011)
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        name = frame.f_code.co_name
        lineno =  frame.f_lineno

        #check for breakpoints
        filename = self._abs_filename( filename )
        bps = self.bpoints.filter( ('filename','lineno'), (filename,lineno) )
        for bpdata in bps:
            self._paused = self._hit_bp( bpdata, frame)
            if self._paused is True:
                break
        
        #-----------------------------------------------------------------------
        #Need to pause/already paused here
        if self._paused is True:
            #This pauses until stepped/resumed
            self._trace_pause(frame, event, arg)
        
        #an exception!
        if event in ('exception','c_exception'):
            self._paused = True            
            self._trace_pause(frame, event, arg)
            
        #-----------------------------------------------------------------------

        #check for step out
        if self._stepout is True:
            #set the previous frame to use the local trace function incase it is
            #not using it already
            frame.f_back.f_trace = self._trace_local
            #and use the stepout function from now on - _trace_local will only be
            #called again when a new breakpoint is encountered or if we are back
            #in the frame above (frame.f_back)
            self._stepout = False
            return self._trace_stepout

        return self._trace_local

    def _trace_stepout(self, frame, event, arg):
        """
        A minimial local trace function used when stepping out of a scope.
        - it will only pause if a breakpoint is encountered (it passes control back to trace_local)
        """
        #check if the engine wants to stop running code
        if self._stop is True:
            raise KeyboardInterrupt

        #check if the debugger want to end debugging.   
        if self._end is True:
            self.write_debug('Ending debugging')
            sys.settrace(None)
            #use a blank trace function as returning None doesn't work
            return self._trace_off

        #file and name of scope being called.
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        name = frame.f_code.co_name
        lineno =  frame.f_lineno

        #check for breakpoints
        filename = self._abs_filename( filename )
        bps = self.bpoints.filter( ('filename','lineno'), (filename,lineno) )
        for bpdata in bps:
            will_break = self._check_bp( bpdata, frame)
            if will_break is True:
                #do not bother to continue checking
                #pass to the full trace function.
                return self._trace_local(frame, event, arg)
        return self._trace_stepout

    def _trace_pause(self, frame, event, arg):
        """
        A function called from within the local trace function to handle a pauses at this event
        """
        #print the event message to the console     
        filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
        name = frame.f_code.co_name
        lineno = frame.f_lineno
        msg = event+' - '+name+' in '+filename+' at line '+str(lineno)
        if event == 'return':
            msg = msg + ' - result is: '+str(arg)
        elif event == 'exception':
            self.eng.write_stderr(traceback.print_exception(*arg))
        self.write_debug(msg)

        #update the scope list
        self._update_scopes(frame)

        #update stepout flags
        if event=='call':                
            self._can_stepout = False
            self._can_stepin  = True
        elif len(self._scopes)>1:
            self._can_stepout = True
            self._can_stepin  = False
        else:
            self._can_stepout = False
            self._can_stepin  = False

        #send a paused message to the console 
        #(it will publish an ENGINE_DEBUG_PAUSED message after updating internal
        #state)
        #data = (   paused_at=(filename, lineno),
        #           scopes, active_scope,
        #           flags=(can_stepin, can_stepout) ) 
        data =( (name,filename,lineno), 
                self._scopes, self._active_scope, 
                (self._can_stepin,self._can_stepout)    )

        self.eng.publish_msg(   eng_messages.ENGINE_DEBUG_PAUSED+'.'+
                                self.eng.name, data)

        #The user can then select whether to resume, step, step-in, step-out 
        #cancel the code or stop debugging.

        #Make the console prompt for debugger commands at this pause.
        self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                            data=(self.prompt, False))            

        ##Paused loop - waiting for user instructions
        loop = True
        while loop:
            self._resume_event.wait()
            self._resume_event.clear()

            #check if the engine wants to stop running code
            if self._stop is True:
                raise KeyboardInterrupt

            #check if there is user code the execute
            if self._cmd is None: 
                #turn console debug mode off -Note: None to turn off, True/False
                #is line continuation
                self.eng.send_msg( self.eng.console, 
                                    eng_messages.CON_PROMPT_DEBUG, 
                                    data=(self.prompt, None))
                #need to step or resume so exit this while block
                loop = False

            #user command to process.
            else:
                line = self._cmd
                self._cmd = None
                #check for debugger commands
                handled = self._process_dbg_command(line)
                if handled is False:
                    #not a command so execute as python source
                    self._process_dbg_source(line)
        
        #reset stepin flag
        self._can_stepin = False
    
        ##Debugger will run next line
        #check if we have resumed (will not pause again until a breakpoint/pause request)
        if self._resume is True:
            self._paused = False
            self._resume = False
            self._active_scope = 0
            self.write_debug('Resuming')
            #Publish a resumed message
            self.eng.publish_msg(   eng_messages.ENGINE_DEBUG_RESUMED+'.'+
                                    self.eng.name, (None,) )
        #else still paused (will pause at next line)

    def _trace_off(self, frame, event, arg):
        """
        A dummy tracing function used when ending tracing as returning None
        doesn't work (python bug v2.7 as of 01/2011)
        """
        return None

    #---------------------------------------------------------------------------
    # Internal methods
    #---------------------------------------------------------------------------
    def _check_bp(self, bpdata, frame):
        """
        Decide whether to break at the bpdata given. 
        The frame is used to evaluate any conditons.
        """
        bpid = bpdata['id']

        #check if the breakpoint should be ignored.
        #(used to trigger after n hits)
        ignore_count = bpdata['ignore_count']
        icount = self._bp_hcount.get(bpid, 0)
        if (ignore_count is not None) and (icount < ignore_count):   
            #ignoring... 
            return False

        #check if this breakpoint has been triggered enough times
        #(used for temporay breakpoints - only triggered n times)
        trigger_count = bpdata['trigger_count']
        tcount = self._bp_tcount.get(bpid, 0)
        if (trigger_count is not None) and (tcount >= trigger_count):
            #ignoring as already triggered enougth times
            return False

        #checkif there is an expression to evaluate
        condition = bpdata['condition']
        if condition is None:
            #no condition triggering... 
            return True

        #evaluate it
        try:
            trigger = eval(condition, frame.f_globals, frame.f_locals)
        except:
            #fail safe - so trigger anyway.
            return True
        return trigger

    def _hit_bp(self, bpdata, frame):
        """
        Decide whether to break at the bpdata given and update internal counters
        and pause if necesary. The frame is used to evaluate any conditons.

        _hit_bp (this method) will check, update counters and pause if necessary
        _check_bp will only check - not pause or update counters.
        """
        bpid = bpdata['id']

        #increament the hit counter
        hcount = self._bp_hcount.get(bpid, 0)
        self._bp_hcount[bpid] = hcount+1 

        #check if the breakpoint should be ignored.
        #(used to trigger after n hits)
        ignore_count = bpdata['ignore_count']
        if (ignore_count is not None) and (hcount < ignore_count):   
            #ignoring...
            return False

        #check if this breakpoint has been triggered enough times
        #(used for temporay breakpoints - only triggered n times)
        trigger_count = bpdata['trigger_count']
        tcount = self._bp_tcount.get(bpid, 0)
        if (trigger_count is not None) and (tcount >= trigger_count):
            #ignoring as already triggered enougth times
            return False

        #checkif there is an expression to evaluate
        condition = bpdata['condition']
        if condition is None:
            #no condition triggering... increment tcount
            self._bp_tcount[bpid] = tcount+1
            trigger = True
        else:
            #evaluate it
            try:
                trigger = eval(condition, frame.f_globals, frame.f_locals)
            except:
                #fail safe - so trigger anyway.
                self.write_debug('Triger condition expression error - triggering breakpoint')
                bpdata['tcount'] = tcount+1
                trigger =  True

        #increament trigger count and pause
        if trigger is True:
            #triggering... increament tcount
            self._bp_tcount[bpid] = tcount+1
            self.write_debug('Breakpoint triggered')

        return trigger

    def _update_scopes(self, frame):
        scopes = []
        frames = []
        #loop backwards through frames until the bottom frame and generate lists
        #of scope names and frames. 
        while frame is not None:
            name = frame.f_code.co_name
            if name=='<module>':
                filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
                if filename=='<Engine input>':
                    name = 'Main'
            scopes.append(name)
            frames.append(frame)

            #check the next frame back
            if frame == self._bottom_frame:
                frame = None
            else:
                frame = frame.f_back

        #store to internals
        scopes.reverse()
        frames.reverse()
        self._scopes = scopes 
        self._frames = frames

        #set current scope
        level = len(self._scopes)-1
        if self._active_scope!=level:
            self.set_scope(level)

    def _update_frame_locals(self, frame):
        """
        Ensures changes to a frames locals are stored so they are not lost.
        """
        # For explanation see get_scope and the following pages:
        # http://bugs.python.org/issue1654367#
        # http://www.gossamer-threads.com/lists/python/dev/546183
        #use PyFrame_LocalsToFast(f, 1) to save changes back into c array.
        func = ctypes.pythonapi.PyFrame_LocalsToFast
        func.restype=None
        func(ctypes.py_object(frame), 1)

    def _abs_filename(self, filename):
        """
        Internal method to return the absolute filepath form.
        """
        #change filename provided to absolute form
        #This is done using code from the bdb.BdB.canonic() method
        if filename == "<" + filename[1:-1] + ">":
            #file name is a special case - do not modify
            fname = filename
        else:
            #check in cache of filenames already done.
            fname = self._fncache.get(filename,None)
            if not fname:
                #not in cache, get the absolute path
                fname = os.path.abspath(filename)
                fname = os.path.normcase(fname)
                self._fncache[filename] = fname
        return fname

    def _check_files(self, filename, filelist):
        """
        Internal method to check if the file is included in the list (or included
        by a wildcard *).Returns True/False.
        """
        #get absolute filepath form
        fname = self._abs_filename(filename)

        #loop over filelist entries checking each one - return on first positive.
        for f in filelist:
            #a wildcard - check if fname startswith the path upto the *
            if f.endswith('*'):
                if fname.startswith(f[:-1]):
                    return True
            #a normal path - check if fname is this path.
            elif fname==f:
                return True
        return False

    def _process_dbg_command(self, line):
        """
        Check for, and perform user debugger commands.
        Returns handled=True/False
        """
        ##Check for debugger comment commands:
        #
        #STEP #S
        #STEPIN #SI
        #STEPOUT #SO
        #SETSCOPE n #SS n
        #RESUME #R
        #HELP #H
        if line.startswith('#') is False:
            return False

        cmd = line.rstrip('\n') #remove the trailing newline for this check
        parts = cmd.split(' ') #split into command and arguments
        cmd = parts[0]
        args = parts[1:]
        cmd = cmd.lower() #conver to all lower case:

        prompt=True
        #step
        if cmd in ['#step','#s']:
            res = self.step()
            if res is False:
                self.write_debug('Cannot step here')
            else:
                #no need to prompt as stepping
                prompt=False
        #step in
        elif cmd in ['#stepin','#si']:
            res = self.step_in()
            if res is False:
                self.write_debug('Cannot step in here')
            else:
                #no need to prompt as stepping
                prompt=False
        #stepout
        elif cmd in ['#stepout','#so']:
            res = self.step_out()
            if res is False:
                self.write_debug('Cannot step out here')
            else:
                #no need to prompt as stepping
                prompt=False   

        #set scope
        elif cmd in ['#setscope','#ss']:
            if len(args)!=1:
                self.write_debug('Requires an argument that should be a integer scope level (0=main user namespace)')
            try:
                level = int(args[0])
            except:
                level = args[0]
            res = self.set_scope(level)
            if res is False:
                msg = ('Usage: #setscope level\n'+
                'Where level should be an integer, in the range 0 (main user namespace) to '+
                str(len(self._scopes)-1)+' (scope currently being executed)')
                self.write_debug(msg)
        #resume
        elif cmd in ['#resume', '#r']:
            res = self.resume()
            if res is False:
                self.write_debug('Cannot resume here')
            else:
                #no need to prompt as resuming
                pass
            prompt=False
            
        #end debugging
        elif cmd in ['#end', '#e']:
            self.end()
            prompt=False
            
        #help
        elif cmd in ['#help', '#h']:
            self.write_debug(help_msg)
            
        #print line
        elif cmd in ['#line','#l']:
            frame = self._frames[ self._active_scope ]
            tb = inspect.getframeinfo(frame)
            if tb.code_context is None:
                self.write_debug('Source line unavailable')
            else:
                self.write_debug(tb.code_context[tb.index])
        
        #not a debugger command
        else:
            return False
			
        #Prompt for a new command and return
        if prompt is True:
            self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                                (self.prompt, False))
        return True

    def _process_dbg_source(self,line):
        """
        Process a line of user input as python source to execute in the active 
        scope
        """
        ##line is user python command compile it
        ismore,code,err = self.eng.compiler.compile(line)

        #need more 
        #   - tell the console to prompt for more 
        if ismore:
            self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                                (None, True,) )
            return

        #syntax error
        #   - compiler will output the error
        #   - tell the console to prompt for new command 
        if err:
            self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                                (self.prompt, False,) )
            return

        #no code object - could be a blank line
        if code is None:
            self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                                (self.prompt, False,) )
            return

        ##run the code in the active scope
        name, frame, globals, locals = self.get_scope(self._active_scope)
        try:
            exec code in globals,locals
        except SystemExit:
            self.write_debug('Blocking system exit')
        except KeyboardInterrupt:
            self._paused = False
            raise KeyboardInterrupt
        except:
            #engine is exiting   -  probably some error caused by engine exiting
            if self.eng._stop_quiet:
                raise KeyboardInterrupt

            #engine wanted to stop anyway - probably wxPython keyboard interrupt error
            if self._stop is True:
                self._paused = False
                raise KeyboardInterrupt

            #error in user code.
            self.eng.compiler.show_traceback()

        #update the locals
        self._update_frame_locals(frame)

        ##Finished running the code - prompt for a new command
        self.eng.send_msg(  self.eng.console, eng_messages.CON_PROMPT_DEBUG,
                            (self.prompt,False,) )
        
    def write_debug(self, string):
        """
        Write a debugger message to the controlling console
        """
        self.eng.send_msg(  self.eng.console, eng_messages.CON_WRITE_DEBUG,
                            (string,) )

    #---------------------------------------------------------------------------
    # Message handlers
    #---------------------------------------------------------------------------
    def msg_debug_pause(self, msg):
        res=self.pause()
        return res

    def msg_debug_resume(self, msg):
        res=self.resume()
        return res

    def msg_debug_end(self, msg):
        res=self.end()
        return res

    def msg_debug_step(self, msg):
        self.step()

    def msg_debug_stepinto(self,  msg):
        self.step_in()

    def msg_debug_stepout(self, msg):
        self.step_out()

    def msg_debug_setscope(self, msg):
        level = msg.data[0]
        self.set_scope(level)

    def msg_dbg_setbp(self, msg):
        #bpdata= {id,filename, lineno, condition, ignore_count, trigger_count}
        bpdata, = msg.get_data()
        res = self.set_breakpoint(bpdata)
        return res

    def msg_dbg_clearbp(self, msg):
        ids = msg.get_data()
        for id in ids:
            res = self.clear_breakpoint(id)
        return res

    def msg_dbg_editbp(self, msg):
        id,kwargs = msg.get_data()
        res = self.edit_breakpoint(id,**kwargs)
        return res
