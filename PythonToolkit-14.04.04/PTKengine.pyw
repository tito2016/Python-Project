#!/usr/bin/env python
"""
PTK engine launch file - used for launching engines.
"""
import argparse

parser = argparse.ArgumentParser(description='''Start a new PTK engine.''')

#required arguments
parser.add_argument('type',
                    help='''Engine type: "py", "wx", "gtk","gtk3", "qt4", "tk" or "pyside"''') 

#optional arguments
parser.add_argument('label', nargs='?',
                    help='Optional engine label/name to be displayed in PTK')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-c','--connect', nargs=2, 
                    metavar=('HOST', 'PORT'),
                    help='Connect to PTK application')
group.add_argument('-l','--listen', nargs=2,
                    metavar=('PORT', 'ALLOW_EXT'),
                    help='Listen for connecting PTK application')

parser.add_argument('-f','--file', nargs=1, 
                    help='Execute file after starting')
                    
parser.add_argument('-d','--debug', action='store_true', 
                    default=False, 
                    help='Enable debug log')

#get the arguments
args = vars(parser.parse_args())

engtype = args['type']

engname = args.get('name', 'Engine.*')
if (engname.startswith('Engine.') is False):
    engname = 'Engine.'+engname

englabel = args.get('label',None)
connect = args.get('connect',None)
listen = args.get('listen',None)
file = args.get('file', None )
debug = args.get('debug', False)

#check if args has a connect/listen
if (listen is None) and (connect is None):
    parser.print_help()
else:

    #set up the debug log
    import ptk_lib.misc as misc
    if debug is True:
        LOGFILE = misc.USERDIR+'engine.log'
        LOGLEVEL = misc.DEBUG     #Set the log level - DEBUG,INFO,WARNING,ERROR
    else:
        LOGFILE = None
        LOGLEVEL = misc.WARNING
    misc.setup_log(filename=LOGFILE, level=LOGLEVEL)
    del LOGFILE, LOGLEVEL, misc

    #---------------------------------------------------------------------------
    import logging
    log = logging.getLogger(__name__)
    #---------------------------------------------------------------------------
    log.info('Engine type: '+str(engtype))
    if engtype == 'py':
        from ptk_lib.engine.py_engine import pyEngine as Engine

    elif engtype == 'wx':
        from ptk_lib.engine.wx_engine import PTK_wxEngine as Engine

    elif engtype == 'gtk':
        from ptk_lib.engine.gtk_engine import PTK_gtkEngine as Engine

    elif engtype == 'gtk3':
        from ptk_lib.engine.gtk3_engine import PTK_gtk3Engine as Engine

    elif engtype == 'qt4':
        from ptk_lib.engine.qt4_engine import PTK_qt4Engine as Engine

    elif engtype == 'tk':
        from ptk_lib.engine.tk_engine import PTK_TkEngine as Engine

    elif engtype == 'pyside':
        from ptk_lib.engine.pyside_engine import PTK_pysideEngine as Engine

    elif engtype == 'remote':
        raise NotImplementedError('Remote engine not implemented yet')
    else:
        raise Exception('Unknown engine type: '+str(engtype))

    #create the engine
    log.info('Creating engine process.')
    eng = Engine(englabel)
    
    #connect to message bus
    if connect is not None:
        log.info('Connecting to messagebus'+str(connect) )
        host,port = connect
        eng.connect( host, int(port) )

    elif listen is not None:
        log.info('Listening for messagebus connection')
        port, allow_ext = listen
        eng.listen( int(port), bool(allow_ext) )

    else:
        raise Exception('Need to specifiy -c [--connect] or -l [--listen]')

    #run a file
    if file is not None:
        log.info('Engine started with file to execute, executing :'+str(file))
        import time
        while engine.console is None:
            time.sleep(0.1)
        try:
            eng.push_line( 'execfile(r"' +file[0]+'")')
        except:
            log.exception('Error in file!')
            
    #start mainloop
    log.info('Starting mainloop.')
    eng.start_main_loop()
    
    #shutdown cleanly
    eng.shutdown()      #call client shutdown method to ensure comms thread has stopped
    log.info('Exiting.')
    logging.shutdown()


