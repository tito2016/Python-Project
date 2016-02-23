"""
Addressed controls - add elements using a string address system.


AddressedMenu     - A menu control using addresses to add items.
AddressedTreeCtrl - A modified tree control using addresses to add items.
"""
import wx

class AddressedMenu(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)
        self.submenus={}
    
    def Append(self,id,address,help, kind=wx.ITEM_NORMAL):
        """
        Append a menu item to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.Append(menu,id, name, help, kind)
        return item

    def Insert(self,pos, id,address,help, kind=wx.ITEM_NORMAL):
        """
        Insert a menu item to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.Insert(menu,pos,id, name, help, kind)
        return item

    def AppendItem(self,id,address,help):
        """
        Append a menu item to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.MenuItem(menu, id,text=name,help=help)
        wx.Menu.AppendItem(menu,item)
        return item

    def InsertItem(self,pos,id,address,help):
        """
        Insert a menu item to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.MenuItem(menu, id,text=name,help=help)
        wx.Menu.InsertItem(menu,pos,item)
        return item

    def AppendCheckItem(self, id, address, help):
        """
        Append a check item to to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.AppendCheckItem(menu,id,name,help)
        return item
    
    def InsertCheckItem(self,pos, id, address, help):
        """
        Insert a check item to to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.InsertCheckItem(menu,pos,id,name,help)
        return item

    def AppendRadioItem(self, id, address, help):
        """
        Append a radio item to to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.AppendRadioItem(menu,id,name,help)
        return item
    
    def InsertRadioItem(self, pos, id, address, help):
        """
        Append a radio item to to the sub menu given by the address.
        where address='sub_menu\\sub_submenu\\item name' 
        Returns the item object
        """
        root,sep,name = address.rpartition('\\')
        menu = self.GetMenu(root)
        item = wx.Menu.InsertRadioItem(menu,pos, id,name,help)
        return item

    def AppendSeparator(self,address=''):
        """
        Append a seperator item to the sub menu given by the address.
        Returns the item object
        """
        menu = self.GetMenu(address)
        item = wx.Menu.AppendSeparator(menu)
        return item

    def InsertSeparator(self,pos, address=''):
        """
        Append a seperator item to the sub menu given by the address.
        Returns the item object
        """
        menu = self.GetMenu(address)
        item = wx.Menu.InsertSeparator(menu, pos)
        return item

    def AppendSubMenu(self, *args, **kwargs):
        raise Exception('Use the address system to add submenus automatically that can be addressed')

    def AppendMenu(self, *args, **kwargs):
        raise Exception('Use the address system to add submenus automatically that can be addressed')

    def InsertSubMenu(self, *args, **kwargs):
        raise Exception('Use the address system to add submenus automatically that can be addressed')

    def InsertMenu(self, *args, **kwargs):
        raise Exception('Use the address system to add submenus automatically that can be addressed')

    def GetMenu(self, address):
        """
        Get the menu corresponding to the address above.
        Returns 
        """
        if address=='':
            return self

        menu_name,sep,sub_address = address.partition('\\')
        #get/create the menu called menu_name
        if self.submenus.has_key(menu_name) is False:
            #create sub menu
            submenu = AddressedMenu()
            wx.Menu.AppendSubMenu(self,submenu, menu_name)
            self.submenus[menu_name]=submenu
        else:
            submenu = self.submenus[menu_name] 
        if sub_address == '':
            return submenu
        #this is not the menu you are looking for...
        menu = submenu.GetMenu(sub_address)
        return menu

class TestMenuFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1,'test frame')
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRDown)

        self.menu = AddressedMenu()
        self.menu.AppendItem(-1,'item1','')
        self.menu.AppendSeparator('') 
        self.menu.AppendItem(-1,'sub1\\item1','') 
        self.menu.AppendSeparator('') 
        self.radio = self.menu.AppendRadioItem(-1,'Radio item2','')
        self.check = self.menu.AppendCheckItem(-1,'sub1\\check item2','')
        self.menu.AppendItem(-1,'sub1\\subsub1\\item1','')
        self.menu.AppendCheckItem(-1,'sub1\\subsub1\\another sub\\a','')
        self.menu.AppendRadioItem(-1,'sub1\\subsub1\\item2','')
        self.menu.AppendItem(-1,'item3','')

    def OnRDown(self,event):
        #display the menu
        self.PopupMenu(self.menu)


class AddressedTreeCtrl(wx.TreeCtrl):
    def __init__(self, *args, **kwargs):
        """
        A modified TreeCtrl using addresses to add items, along with automatic
        sorting of children.
        """
        wx.TreeCtrl.__init__(self, *args, **kwargs)

    def AddItem(self,address='\\child', pydata=None, image=-1):
        """
        Add an item to the tree at the address given.
        """

        #check if the item already exists
        if self.ItemExists(address) is True:
            raise Exception('Item address already exists')

        #check if the parent item exists
        parent,sep,name = address.rpartition('\\')
        if self.ItemExists(parent) is False:
            raise Exception('Item address\' parent does not exist')

        #get parent and create new child
        parentitem = self.GetItem(parent)
        child = self.AppendItem(parentitem, name, image)
        self.SetItemPyData(child,pydata)
        self.SortChildren(parentitem)

    def GetItem(self,address='\\'):
        """
        Find the item for the address specified.
        address = '\\' is the root item
        address = '\\item1' is a child of the root item
        address = ''\\item1\\sub1' is  a child of item1
        """
        if address=='':
            return self.GetRootItem()

        parent,sep,name = address.rpartition('\\')
        if parent=='':
            parent_item = self.GetRootItem()
        else:
            parent_item = self.GetItem(parent)
        
        #find the correct child
        nextchild,cookie = self.GetFirstChild(parent_item)
        while (nextchild.IsOk()):
            if self.GetItemText(nextchild) == name:
                return nextchild
            nextchild = self.GetNextSibling(nextchild)
        raise Exception('Item not found')

    def ItemExists(self,address='\\'):
        """
        Check if the item at the address given exists
        """
        if address=='':
            return True

        parent,sep,name = address.rpartition('\\')
        if parent=='':
            parent_item = self.GetRootItem()
        else:
            if self.ItemExists(parent):
                parent_item = self.GetItem(parent)
            else:
                return False

        #find the correct child
        nextchild,cookie = self.GetFirstChild(parent_item)
        while (nextchild.IsOk()):
            if self.GetItemText(nextchild) == name:
                return True
            nextchild = self.GetNextSibling(nextchild)
        return False

    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        if t1 < t2: return -1
        if t1 == t2: return 0
        return 1
