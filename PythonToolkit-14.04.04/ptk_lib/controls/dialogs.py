"""
Useful wx python help functions for dialogs
"""

import wx
__all__ = ['Message','ConfirmDialog']

#---Message dialog--------------------------------------------------------------
def Message(message,title):
    """Open a message dialog"""
    dlg = wx.MessageDialog(None, message,title,wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()

#---Confirm dialog--------------------------------------------------------------
def ConfirmDialog(message,title):
    """open a confirmation dialog, returns true/false"""
    dlg = wx.MessageDialog(None, message,title,wx.OK |wx.CANCEL| wx.ICON_EXCLAMATION)
    val = dlg.ShowModal()
    dlg.Destroy()
    if val==wx.ID_OK:
        return True
    if val==wx.ID_CANCEL:
        return False

