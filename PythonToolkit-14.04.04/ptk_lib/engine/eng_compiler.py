"""
Engine Compiler
---------------

Handles the compilation of source and formating exceptions and tracebacks for 
the engine.
"""

#---logging---------------------------------------------------------------------
import logging
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)

from codeop import _maybe_compile, Compile
import sys
import traceback                        #for formatting errors

import eng_messages                     #standard engine message types

class EngineCompiler(Compile):
    def __init__(self, eng):
        Compile.__init__(self)

        #parent engine
        self.eng = eng

        #the number of lines to remove from the traceback line count, 
        #for multi line hack in compilation stage
        self._lineadjust = 0  

        #source buffer to get print line of source in exception
        self._buffer = '' 
        
        #register message handlers
        self.eng.set_handler(eng_messages.ENG_FUTUREFLAG, self.msg_future_flag)

    #---------------------------------------------------------------------------
    # Interface methods
    #---------------------------------------------------------------------------
    def set_compiler_flag(self,flag,set=True):
        """
        Set or unset a __future__ compiler flag
        """
        if set is True:
            self.flags |= flag
        else:
            self.flags &= ~flag

    def compile(self,source):
        """
        Compile source. 
        Returns (more,code,err) where:
            
        more        -   Bool indicating whether more is expected
        code        -   the compiled code object if any
        err         -   True if syntax error, false otherwise
        """
        ##to enable more lines when the current code is ok but not finished we 
        ##remove the final \n, this means the line must have \n\n to be complete.
        if source[-1]=='\n':
            source = source[:-1]

        ##check that the line is not empty
        if source.lstrip()=='':
            return False,None,False

        ##to enable multiple lines to be compiled at once we use a cheat...
        ##everything is enclosed in if True: block so that it will compile as a 
        ##single line, but need to check that there is no indentation error...
        if source[0]!=' ': #check for first line indentation error
            self._lineadjust=-1
            lastline = source.split('\n')[-1]
            source ="if True:\n "+source.replace('\n','\n ')
            #the old source ended with a '\n' no more to come so add '\n' 
            #so that it compiles
            if source.endswith('\n '):
                source = source+'\n'
            #also if the last line is zero indent add a \n as the block is also
            #complete
            if (len(lastline)-len(lastline.lstrip()))==0:
                source = source+'\n'
        else:
            self._lineadjust=0

        #store source in buffer
        self._buffer = source        

        ##now compile as usual.
        filename="<Engine input>"
        symbol="single"
        try:
            code = _maybe_compile(self, source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1 - syntax error
            self.show_syntaxerror()
            return False,None,True

        if code is None:
            # Case 2 - more needed
            return True,None,False

        # Case 3 - compile to code
        return False,code,False

    def show_syntaxerror(self):
        """
        Display the syntax error that just occurred.
        This doesn't display a stack trace because there isn't one.

        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).

        taken from: code.InteractiveInterpreter
        """
        filename="<Engine input>"
        
        errtype, value, sys.last_traceback = sys.exc_info()
        sys.last_type = errtype
        sys.last_value = value
            
        try:
            msg, (dummy_filename, lineno, offset, line) = value
        except:
            # Not the format we expect; leave it alone
            pass
        else:
            if dummy_filename==filename:
                #(lineno-1 due to multiline hack in compile source)
                value = errtype(msg, (filename, lineno+self._lineadjust, offset, line))
            else:
                value = errtype(msg, (dummy_filename, lineno, offset, line))
            sys.last_value = value
        list = traceback.format_exception_only(errtype, value)
        map(sys.stderr.write, list)

    def show_traceback(self):
        """
        Display the exception that just occurred.
        We remove the first stack item because it is our own code and adjust the
        line numbers for any engine inputs.
        modified from: code.InteractiveInterpreter
        """
        try:
            type, value, sys.last_traceback = sys.exc_info()
            sys.last_type = type
            sys.last_value = value
            tblist = traceback.extract_tb(sys.last_traceback)
            del tblist[:1] #in our code so remove

            for  n in  range(0,len(tblist)):
                filename, lineno, offset, line = tblist[n]
                if filename =="<Engine input>":
                    #alter line number
                    tblist[n] = (filename, lineno+self._lineadjust, offset, line)
                list = traceback.format_list(tblist)
                if list:
                    list.insert(0, "Traceback (most recent call last):\n")
                list[len(list):] = traceback.format_exception_only(type, value)
            map(sys.stderr.write, list)
        except:
            pass
    #---------------------------------------------------------------------------
    # Message handlers
    #---------------------------------------------------------------------------
    def msg_future_flag(self, msg):
        """enable or disable a __future__ feature using flags"""
        flag,set = msg.get_data()
        self.set_compiler_flag(flag,set)
   
