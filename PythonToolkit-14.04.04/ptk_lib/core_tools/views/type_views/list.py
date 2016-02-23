"""
Type view for python lists
"""

from viewer import TypeView
import wx
import  wx.grid

#---list view-------------------------------------------------------------------
class ListView(TypeView):
    """List viewer"""
    def __init__(self,viewer,oname,eng):
        TypeView.__init__(self,viewer,oname,eng)

        self.table = ListTable(viewer.viewtool,oname,eng)
        self.grid = wx.grid.Grid(self,-1)
        self.grid.SetTable(self.table)
        self.grid.SetColLabelSize(17)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.grid,1,wx.EXPAND|wx.ALL,0)
        self.RefreshView()

    def RefreshView(self):
        """Update the grid array size if needed"""
        #this updates the grid directly
        self.table.RefreshTable()

    def DisableView(self):
        self.disabled = True
        self.grid.Disable()
        self.table.Disable()
        self.Disable()

    def EnableView(self,eng):
        self.eng = eng
        self.disabled = False
        self.grid.Enable()
        self.table.Enable(eng)
        self.Enable()

#---List table------------------------------------------------------------------
class ListTable(wx.grid.PyGridTableBase):
    """A custom grid table to get data from a list"""
    def __init__(self, viewtool, oname,eng):
        wx.grid.PyGridTableBase.__init__(self)
        self.viewtool = viewtool

        #the list this table represents
        self.oname = oname
        self.eng=eng

        #Store some info about the list
        self.len = self.eng.evaluate('len('+self.oname+')')

        #set some table/grid attributes
        self.cell=wx.grid.GridCellAttr()
        self.cell.SetBackgroundColour(wx.WHITE)
    
        self.disabled = False

    #---Overloaded methods for this virtual grid--------------------------------
    def GetAttr(self, row, col, kind):
        self.cell.IncRef()
        return self.cell

    def GetNumberRows(self):
        return 1
        
    def GetNumberCols(self):
        return self.len

    def IsEmptyCell(self, row, col):
        return False
        
    def GetValue(self, row, col):
        if self.disabled:
            return ''
        #we display the string representation of the object in the cell.
        value = self.eng.evaluate('str('+self.oname+'['+str(col)+'])')
        return value

    def SetValue(self, row, col, value):
        if self.disabled:
            return
        #we set the value to the string expression entered
        self.eng.execute(self.oname+'['+str(col)+']='+str(value))
        #publish engine state change message
        self.eng.notify_change()

    def GetColLabelValue(self,col):
        return col

    def GetRowLabelValue(self, row):
        return ''

    def RefreshTable(self):
        """Update the table shape and ndim and adjust the grid as needed"""
        if self.disabled:
            return

        len = self.eng.evaluate('len('+self.oname+')')

        #get old size
        oldcols = self.len
        
        #calculate adjustment
        coladjust = len-oldcols
    
        #store new length
        self.len = len

        #apply adjustments if needed
        view = self.GetView()
        if coladjust <0:
            #delete cols
            m = wx.grid.GridTableMessage(self,wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED,0,-coladjust)
            view.ProcessTableMessage(m)
        elif coladjust>0:
            #add cols
            m = wx.grid.GridTableMessage(self,wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED,coladjust)
            view.ProcessTableMessage(m)
        view.ForceRefresh()

    def Disable(self):
        self.disabled = True
        self.eng = None

    def Enable(self,eng):
        self.eng = eng
        self.disabled = False
        self.RefreshTable()
