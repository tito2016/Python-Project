"""
Type view for arrays
"""
from ptk_lib.core_tools.views import TypeView
import wx
import  wx.grid

class ArrayView(TypeView):
    """Array viewer"""
    def __init__(self, viewer, oname, eng):
        TypeView.__init__(self, viewer, oname, eng)

        self.table = ArrayTable(oname,eng)
        self.grid = wx.grid.Grid(self,-1)
        self.grid.SetTable(self.table)
        self.grid.SetColLabelSize(17)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.grid,1,wx.EXPAND|wx.ALL,0)
        self.RefreshView()

    def RefreshView(self):
        """Update the grid array size if needed"""
        if self.disabled:
            return

        ndim = self.eng.evaluate(self.oname+'.ndim')
        if ndim >2:
            self.viewer.ShowMessage('Cannot display arrays with more than two dimensions','info')
        #this updates the grid directly
        #self.table.RefreshTable()

    def DisableView(self):
        """Overloaded DisableView method"""
        self.disabled = True
        self.grid.Disable()
        self.table.Disable()
        self.Disable()

    def EnableView(self,eng):
        """Overloaded EnableView method"""
        self.eng = eng
        self.disabled = False
        self.grid.Enable()
        self.table.Enable(eng)
        self.Enable()

#---------------------------------------------------------------------------
class ArrayTable(wx.grid.PyGridTableBase):
    """A custom grid table to get data from an array (of upto 2dimensions)"""
    def __init__(self, oname,eng):
        wx.grid.PyGridTableBase.__init__(self)
        self.oname = oname
        self.eng=eng
        self.disabled = False

        #reference to message bus for sending engine state change msesages
        app = wx.GetApp()
        self.msg_bus = app.msg_bus

        #set some table/grid attributes
        self.cell=wx.grid.GridCellAttr()
        self.cell.SetBackgroundColour(wx.WHITE)
        
        self.shape,self.ndim = self.eng.evaluate('('+self.oname+'.shape ,'+self.oname+'.ndim )')


    #---Overloaded methods for this virtual grid--------------------------------
    def GetAttr(self, row, col, kind):
        self.cell.IncRef()
        return self.cell

    def GetNumberRows(self):
        if self.ndim == 1:
            return 1
        elif self.ndim == 2: 
            return self.shape[0]
        else:
            return 1
        
    def GetNumberCols(self):
        if self.ndim == 1:
            return self.shape[0]
        elif self.ndim == 2:
            return self.shape[1]
        else:
            return 1

    def IsEmptyCell(self, row, col):
        return False
        
    def GetValue(self, row, col):
        if self.disabled:
            return ''
        if self.ndim ==1:
            value = self.eng.evaluate(self.oname+'['+str(col)+']')
        elif self.ndim ==2 :
            value = self.eng.evaluate(self.oname+'['+str(row)+','+str(col)+']')
        else:
            value = ''
        return value

    def SetValue(self, row, col, value):
        if self.disabled:
            return None
        if self.ndim == 1:
            self.eng.execute(self.oname+'['+str(col)+']='+str(value))
        elif self.ndim == 2:
            self.eng.execute(self.oname+'['+str(row)+','+str(col)+']='+str(value))
        #publish engine state change message
        self.eng.notify_change()

    def GetColLabelValue(self,col):
        if self.ndim<=2:
            return str(col)
        else:
            return ''

    def GetRowLabelValue(self, row):
        if self.ndim==1 or self.ndim==2:
            return str(row)
        else:
            return ''

    def RefreshTable(self):
        """Update the table shape and ndim and adjust the grid as needed"""
        if self.disabled:
            return

        shape,ndim = self.eng.evaluate('('+self.oname+'.shape ,'+self.oname+'.ndim )')
        
        #get old size
        if self.ndim==1:
            oldrows = 1
            oldcols = self.shape[0]
        elif self.ndim==2:
            oldrows,oldcols = self.shape
        else:
            oldrows,oldcols = (1,1)
        
        #calculate adjustment
        if ndim==1:
            rowadjust = 1-oldrows
            coladjust = shape[0]-oldcols
        elif ndim==2:
            rowadjust = shape[0]-oldrows
            coladjust = shape[1]-oldcols
        else:
            rowadjust = 1-oldrows
            coladjust = 1-oldcols

        #store new shape and ndim
        self.ndim=ndim
        self.shape=shape

        #apply adjustments if needed
        view = self.GetView()
        if rowadjust <0:
            #delete rows
            m = wx.grid.GridTableMessage(self,wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,0,-rowadjust)
            view.ProcessTableMessage(m)
        elif rowadjust>0:
            #add rows
            m = wx.grid.GridTableMessage(self,wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,rowadjust)
            view.ProcessTableMessage(m)
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

    def Enable(self,eng):
        self.eng = eng
        self.disabled = False
        self.RefreshTable()
