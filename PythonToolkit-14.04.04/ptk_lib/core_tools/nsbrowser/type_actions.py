"""
NSBrowser type actions - a container object for NSBrowser actions things that 
can be done on objects of certain types.

Actions show up in the NSBrowser context menus for the type given in 
Action.type_strings at the menu location specified by address.

I.e. 'Export\\As text file'   - Would appear as an entry 'As text file' in a sub
menu 'Export'
"""
class Action():
    def __init__(self, address, type_strings, helptip='', multi=True):
        """
        Create an importer for the filetypes given by the list of file_exts.
        
        address         -   the name/address string to display for this action.
                            e.g) Browse To or Export\As text file
        type_strings    -   list of supported python types
        helptip         -   a helptip string to use.
        multi           -   True if this action can handle multiple objects
        """
        self.address = address
        self.type_strings = type_strings
        self.helptip = helptip
        self.multi = multi

    def __call__(self, engname, obj_names):
        """
        Call the Action with the list of object names
        """
        pass

    def can_handle(self, type_strings):
        """
        Check if this action can handle objects with the types give.
        If this action can only handle one object at a time it should
        return False if len(type_strings)>1.
        """
        #check if this object can handle multiple objects
        if len(type_strings)>1 and self.multi is False:
            return False

        #check if this action can handle all types.
        if -1 in self.type_strings:
            return True

        res = True
        for type in type_strings:
            if type not in self.type_strings:
                res = False
                break
        return res

    def get_name(self):
        """
        Get the Action name
        """
        return self.name

    def get_helptip(self):
        """
        Get a helptip for this exporter
        """
        return self.helptip

#-------------------------------------------------------------------------------
class BrowseToAction(Action):
    def __init__(self, nsb):
        Action.__init__(self, 'Browse To',
                            type_strings=[-1], 
                            helptip='Display the object in the namespace browser', 
                            multi=False)
        self.nsb = nsb

    def __call__(self, engname, obj_names):
        self.nsb.browse_to(engname, obj_names[0])
