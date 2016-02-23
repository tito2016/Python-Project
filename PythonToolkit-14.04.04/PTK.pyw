#!/usr/bin/env python
"""
Main PTK launch file - used for launching the application.
"""
import argparse
import os
import logging
import wx
from ptk_lib import misc
import ptk_lib.app as app

def clear_settings():
    #create the application instance
    _app = wx.PySimpleApp()
    msg = 'Clear all PTK settings'
    title = 'Clear PTK Settings'
    dlg = wx.MessageDialog(None, msg,title,wx.OK |wx.CANCEL| wx.ICON_EXCLAMATION)
    val = dlg.ShowModal()
    dlg.Destroy()
    if val==wx.ID_OK:
        from ptk_lib import misc
        cfg = wx.FileConfig(localFilename=misc.USERDIR+'options')
        cfg.DeleteAll()
        
#-------------------------------------------------------------------------------
#get input arguments using argparse module
parser = argparse.ArgumentParser(
        description='PTK (PythonToolKit)- an interactive python environment' )
#optional arguments
parser.add_argument('-c','--clear_settings', action='store_true', default=False,
                    help='Connect to PTK application')
parser.add_argument('-f','--files',nargs='*', metavar='filename(s)', default=[], 
                    help='Open the files in the editor')
parser.add_argument('-d','--debug',action='store_true', default=False, 
                    help='Enable logging of debug statements')

#get the arguments
args = vars(parser.parse_args())
if args.get('clear_settings', False) is True:
    clear_settings()
else:
    #create the application instance
    _app = app.PTKApp(name='PTK', args=args)
    #start main loop
    _app.MainLoop()


