"""
Module defining the Engine message types used for control/communication between
engines and the main PTK console via the MessageBus system.

ENG* messages are engine control messages
CON* messages are console control messages

ENGINE* messages are published messages about the engine state.
"""

#---Connection------------------------------------------------------------------
#Sent by the console asigned to control the engine. The from node name is then 
#used for future communications with the console.
# data=None
# result = engine info dictionary
ENG_MANAGE = 'Eng.Manage'

#Sent by the console managing the engine to 'release' it.
# data=None
# result=True/False if the release was succesful
ENG_RELEASE = 'Eng.Release'

#---Engine control messages-----------------------------------------------------
#
# Sent to the engine from the console.
#Push a line of user input to the engine:  data=string, reply=None
ENG_PUSH = 'Eng.Push'       

#Attempt to stop a running user command by raising a keyboard interrupt, reply=None.
ENG_STOP   = 'Eng.Stop'

#execute statement in process, data=string, reply=None
ENG_EXECCOMMAND = 'Eng.ExecCommand'                       

#evaluate statement in process, data=string, reply=result
ENG_EVALCOMMAND = 'Eng.EvalCommand'                      

#register a task with the engine process, data=(name,code),reply=None
ENG_REGISTERTASK = 'Eng.RegisterTask'     

#Exectute a task in process, data=code, reply=result
ENG_RUNTASK = 'Eng.RunTask'               

#Add a function to the engines builtin module, data=marshalled code, reply=result
ENG_ADDBUILTIN = 'Eng.AddBuiltin'   

#Enable or disable the future flags from the process compiler, 
#data=(flag, set=True/False)
ENG_FUTUREFLAG = 'Eng.FutureFlag'  

#Get the engine state reply= (busy, debug,profile, paused)
ENG_GETSTATE = 'Eng.GetState'  

#Get a list of the registered engine task names, reply= (taskname1, taskname2, ...)
ENG_GETTASKS = 'Eng.GetTasks'  

##Debugger

#Toggle debug/traceback mode, data=enable (True/False), reply=state (True/False)
ENG_DEBUG_TOGGLE = 'Eng.Debug.Toggle' 

#Pause running user command, reply=sucess (True/False)
ENG_DEBUG_PAUSE  = 'Eng.Debug.Pause'

#Resume running user command, reply=sucess (True/False)
ENG_DEBUG_RESUME = 'Eng.Debug.Resume'         

#End debugging and finish running the user command, reply=sucess (True/False)
ENG_DEBUG_END = 'Eng.Debug.End' 

#Step to next command in debugger, reply=sucess (True/False)
ENG_DEBUG_STEP   = 'Eng.Debug.Step'         

#Step-into scope (only when debugger is on the 'call'), reply=sucess (True/False) 
ENG_DEBUG_STEPIN = 'Eng.Debug.StepIn' 

#Step-out of scope (no traceback until scope finishes, reply=sucess (True/False)
ENG_DEBUG_STEPOUT = 'Eng.Debug.StepOut'    

#Set the active scope for interogation, data=level, reply=None
ENG_DEBUG_SETSCOPE = 'Eng.Debug.SetScope'

#Set a debugger break point,
# data=(bpdata= {id,filename, lineno, condition, ignore_count, trigger_count}
# reply=sucess (True/False)
ENG_DEBUG_SETBP = 'Eng.Debug.SetBP'         

#Clear a debugger breakpoint(s)
# data = (id,) (id=None clears all breakpoints)
# reply=sucess (True/False)
ENG_DEBUG_CLEARBP = 'Eng.Debug.ClearBP'              

#Change a debugger breakpoint
# data = (id, kwargs=(filename, lineno, condition,ignore_count,trigger_count))
# reply=sucess (True/False)
ENG_DEBUG_EDITBP = 'Eng.Debug.EditBP'

##profiler
#Toggle profiler mode, data=enable (True/False), reply=state (True/False)
ENG_PROFILE_TOGGLE = 'Eng.Profile.Toggle'

#---Console control messages----------------------------------------------------
#
# Sent to the console from the engine.
# Some are sent before a published messages to allow the console to update it's
# internal state before subscribers may want to access it.

#Prompt for next input, data=more (True/False/None=disable prompt), reply=None
CON_PROMPT = 'Con.Prompt'

#Read from stdin, data=more(True/False/None=disable prompt), reply=None
CON_PROMPT_STDIN = 'Con.Prompt.StdIn'           

#Prompt for debugger commands data=more (True/False/None=disable prompt), reply=None
CON_PROMPT_DEBUG = 'Con.Prompt.Debug'

#Write to stdout, data=string, reply=None
CON_WRITE_STDOUT = 'Con.Write.StdOut'       

#Write to stdout, data=string, reply=None
CON_WRITE_STDERR = 'Con.Write.StdErr'    

#Clear the console, data=None, reply=None
CON_CLEAR = 'Con.Clear'

#Execute the source lines as if entered by the console by the user, data=(Source,), reply=None
CON_EXECSOURCE = 'Con.ExecSource'

##Debugger
#Write a debugger message, data=string, reply=None
CON_WRITE_DEBUG = 'Con.Write.Debug'

#---Published messages----------------------------------------------------------
#
# Published by the engine.

#Engine is executing a user command (published after CON_BUSY sent to console),
# data=(debug, profile)
ENGINE_STATE_BUSY    = 'Engine.State.Busy' 

#Engine has finished exectuing a user command completly and is waiting for new 
#input. data= (debug, profile)
ENGINE_STATE_DONE    = 'Engine.State.Done'

# Published by the engine (or others) when the state of objects in the engine 
# may have changed. i.e. data has been imported. data=(busy, debug, profile)
ENGINE_STATE_CHANGE = 'Engine.State.Change'

#Published by the engine when user input has been sucessfully pushed to the 
#engine this could a line of code, debugger command or standard input
# data= (line, type='CMD','DBG_CMD','INPUT') where type indicates how it was 
#processed.
ENG_LINE_PROCESSED = 'Engine.LineProcessed' 

##Debugger
#subject group for debugger messages
ENGINE_DEBUG = 'Engine.Debug'

#published when the debugger mode is enabled, data= (enabled=True/False)
ENGINE_DEBUG_TOGGLED = 'Engine.Debug.Toggled'

#paused code_   data=( paused_at=(scope, filename, lineno),
# scope_list, active_scope, flags=(can_stepin,can_stepout) )
ENGINE_DEBUG_PAUSED = 'Engine.Debug.Paused'

#resumed code. data=(,)
ENGINE_DEBUG_RESUMED = 'Engine.Debug.Resumed'

#debugger active scope changed, data=( scopes_list, active_scope)
ENGINE_DEBUG_SCOPECHANGED = 'Engine.Debug.ScopeChanged'

##Profiler

#published when the profiler mode is enabled, data= (enabled=True/False)
ENGINE_PROFILE_TOGGLED = 'Engine.Profile.Toggled'
