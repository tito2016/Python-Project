"""
Package name: controls
-------------

Description:
------------

This module contains various custom wxpython controls that can be resused.

addressed_ctrls - Add elements using a string address system. 
                    (AddressedMenu - A menu control using addresses to add items and 
                    AddressedTreeCtrl - A modified tree control using addresses)
controls        - general controls
icon_button     - A collection of icon/button controls for use in frames/dialogs without 
                    title bars including some simple icons.   
info_ctrl       - A general report/info control with icon/label/value, label/value or 
                    collapsible items.
"""
from controls import *
from addressed_ctrls import AddressedTreeCtrl, AddressedMenu
from dialogs import *
