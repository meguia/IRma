# CTK Utils
# CTkTable with checkboxes based on the Widget by Akascape
# License: MIT

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from PIL import Image

dark_color = "#5a5a5a"
NavigationToolbar2Tk.toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to  previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )


def any_to_stringvar(value):
    if isinstance(value, str):
        return ctk.StringVar(value=value)
    elif isinstance(value, int):
        return ctk.StringVar(value=str(value))
    elif isinstance(value, list):
        return ctk.StringVar(value=','.join(map(str,value)))
    else:
        return ctk.StringVar(value="")

def ctkstring_to_value(ctkstring, type='str', convert=False):
    if ctkstring.get() == "":
        return None
    if type == 'str':
        return ctkstring.get()
    elif type == 'int':
        return int(ctkstring.get())
    elif type == 'list':
        if convert:
            return list(map(int, ' '.join(ctkstring.get().split(',')).split()))
        else:  
            return ' '.join(ctkstring.get().split(',')).split()
    else:
        return None
    
def figure_to_image(fig,width=500,height=400):
    fig.savefig(r"temp.png", dpi=300)
    return ctk.CTkImage(Image.open(r"temp.png"),size=(width,height))
    

class CustomToolbar(NavigationToolbar2Tk):  # for matplotlib 3.7.1
    def __init__(self, figcanvas, parent):
        super().__init__(figcanvas, parent) 

    def draw_rubberband(self, event, x0, y0, x1, y1):
        self.canvas._tkcanvas.delete(self.canvas._rubberband_rect_white)
        height = self.canvas.figure.bbox.height
        y0 = height - y0
        y1 = height - y1
        self.canvas._rubberband_rect_white = self.canvas._tkcanvas.create_rectangle(x0, y0, x1, y1,outline='white', dash=(3, 3))

class CustomToolbar_old(NavigationToolbar2Tk):  # for matplotlib 3.5.2
    def __init__(self, figcanvas, parent):
        super().__init__(figcanvas, parent)  

    def draw_rubberband(self, event, x0, y0, x1, y1):
        self.remove_rubberband()
        height = self.canvas.figure.bbox.height
        y0 = height - y0
        y1 = height - y1
        self.lastrect = self.canvas._tkcanvas.create_rectangle(x0, y0, x1, y1,outline = 'white', dash=(3, 3))           

class PlotFrame(ctk.CTkFrame):
    """ Matplotlib PlotFrame Widget"""
    def __init__(self, parent, figure=None, axes=None, **kwargs):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        self.figure = figure if figure is not None else Figure()
        self.axes = axes if axes is not None else self.figure.add_subplot(111)
        
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        #self.toolbar = CustomToolbar_old(self.canvas, self)
        self.toolbar = CustomToolbar(self.canvas, self)
        self.toolbar.config(background=dark_color)
        self.toolbar._message_label.config(background=dark_color)
        for button in self.toolbar.winfo_children():
            button.config(background=dark_color)
        self.toolbar.update()
        self.toolbar.pack(side=ctk.BOTTOM, fill=ctk.X)
        
    def update_figure(self, figure):
        self.canvas.figure = figure
        self.canvas.draw()
        #self.toolbar.update()     
        
    def update_axes(self, axes):
        self.axes = axes 
        self.canvas.draw()
        #self.toolbar.update()

    def clear_axes_data(self):
        self.axes.clear()
        self.canvas.draw()
        #self.toolbar.update()    


class CTkTable(ctk.CTkFrame):
    """ CTkTable Widget """
    
    def __init__(
        self,
        master: any = None,
        row: int = None,
        column: int = None,
        checkbox: bool = False,
        padx: int = 1, 
        pady: int = 0,
        values: list = [[None]],
        colors: list = [None, None, None],
        color_phase: str = "rows",
        header_color: bool = False,
        column1st_color: bool = False,
        corner_radius: int = 25,
        **kwargs):
        
        super().__init__(master, fg_color="transparent")

        self.master = master # parent widget
        self.rows = row if row else len(values) # number of default rows
        self.columns = column if column else len(values[0])# number of default columns
        self.checkbox = checkbox # if True then the first column will be checkboxes
        self.padx = padx # internal padding between the rows/columns
        self.pady = pady 
        self.values = values # the default values of the table
        self.checked = [ctk.BooleanVar() for i in range(row)] # list of checked rows
        self.colors = colors # colors of the table if required
        self.header_color = header_color # specify the topmost row color
        self.column1st_color = column1st_color # specify the topmost row color
        self.phase = color_phase
        self.corner = corner_radius
        # if colors are None then use the default frame colors:
        self.fg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"] if not self.colors[0] else self.colors[0]
        self.fg_color2 = ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"] if not self.colors[1] else self.colors[1]
        self.fg_color3 = ctk.ThemeManager.theme["CTkFrame"]["border_color"] if not self.colors[2] else self.colors[2]
        
        self.frame = {}
        self.draw_table(**kwargs)
        
    def draw_table(self, **kwargs):
        """ draw the table """
        for i in range(self.rows):
            for j in range(self.columns):
                if self.phase=="rows":
                    if i%2==0:
                        fg = self.fg_color
                    else:
                        fg = self.fg_color2
                else:
                    if j%2==0:
                        fg = self.fg_color
                    else:
                        fg = self.fg_color2
                        
                if self.header_color:
                    if i==0:
                        fg = self.fg_color3

                if self.column1st_color:
                    if j==0:
                        fg = self.fg_color3       
                        
                corner_radius = self.corner    
                if i==0 and j==0:
                    corners = ["", fg, fg, fg]
                elif i==self.rows-1 and j==self.columns-1:
                    corners = [fg ,fg, "", fg]
                elif i==self.rows-1 and j==0:
                    corners = [fg ,fg, fg, ""]
                elif i==0 and j==self.columns-1:
                    corners = [fg , "", fg, fg]
                else:
                    corners = [fg, fg, fg, fg]
                    corner_radius = 0
                    
                if self.values:
                    try:
                        value = self.values[i][j]
                    except IndexError: value = " "
                else:
                    value = " "
                if self.checkbox and (i>0 and j==0):
                    self.frame[i,j] = ctk.CTkCheckBox(self, fg_color=fg, hover=False, text=value, variable=self.checked[i],**kwargs)
                else:     
                    self.frame[i,j] = ctk.CTkButton(self, background_corner_colors=corners, corner_radius=corner_radius,
                                                          fg_color=fg, hover=False, text=value, **kwargs)
                self.frame[i,j].grid(column=j, row=i, padx=self.padx, pady=self.pady, sticky="nsew")
                
                self.rowconfigure(i, weight=1)
                self.columnconfigure(j, weight=1)
    
    def destroy_table(self, **kwargs):
        """ redraw the table """
        for i in range(self.rows):
            for j in range(self.columns):
                self.frame[i,j].destroy()

    def edit_row(self, row, values,**kwargs):
        """ edit all parameters of a single row """
        if len(values)!=self.columns:
            raise ValueError("The number of values must be equal to the number of columns")
        else:
            for i in range(self.columns):
                self.insert(row, i, values[i], **kwargs)
        
    def edit_column(self, column, values,**kwargs):
        """ edit all parameters of a single column """
        if len(values)!=self.rows:
            raise ValueError("The number of values must be equal to the number of rows")
        else:
            for i in range(self.rows):
                self.insert(i, column, values[i], **kwargs)
            
    def update_values(self, values, **kwargs):
        """ update all values at once """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        self.values = values
        self.draw_table(**kwargs)
        
    def add_row(self, values, index=None):
        """ add a new row """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        if index is None:
            index = len(self.values)      
        self.values.insert(index, values)
        self.rows+=1
        self.checked.insert(index, ctk.BooleanVar())
        self.draw_table()
        
    def add_column(self, values, index=None):
        """ add a new column """
        for i in self.frame.values():
            i.destroy()
        self.frame = {}
        if index is None:
            index = len(self.values[0])
        x = 0
        for i in self.values:
            i.insert(index, values[x])
            x+=1
        self.columns+=1
        self.draw_table()
    
    def delete_row(self, index=None):
        """ delete a particular row """
        if index is None or index>len(self.values):
            index = len(self.values)-1
        self.values.pop(index)
        for i in self.frame.values():
            i.destroy()
        self.rows-=1
        self.frame = {}
        self.draw_table()
        
    def delete_column(self, index=None):
        """ delete a particular column """
        if index is None or index>len(self.values[0]):
            index = len(self.values)-1
        for i in self.values:
            i.pop(index)
        for i in self.frame.values():
            i.destroy()
        self.columns-=1
        self.frame = {}
        self.draw_table()
    
    def insert(self, row, column, value, **kwargs):
        """ insert value in a specific block [row, column] """
        self.frame[row,column].configure(text=value, **kwargs)
    
    def delete(self, row, column, **kwargs):
        """ delete a value from a specific block [row, column] """
        self.frame[row,column].configure(text="", **kwargs)

    def get(self):
        return self.values
    
    def get_checked(self):
        return [self.frame[n,0].cget("text") for n in range(1, self.rows) if self.frame[n,0].get()==1]
    
    def get_checked_indices(self):
        return [n-1 for n in range(1, self.rows) if self.frame[n,0].get()==1]
    
    def get_value(self, row, column):
        return self.frame[row,column].cget("text")
    
    def configure(self, **kwargs):
        """ configure table widget attributes"""
        
        if "colors" in kwargs:
            self.colors = kwargs.pop("colors")
            self.fg_color = self.colors[0]
            self.fg_color2 = self.colors[1]
        if "header_color" in kwargs:
            self.header_color = kwargs.pop("header_color")
        if "rows" in kwargs:
            self.rows = kwargs.pop("rows")
        if "columns" in kwargs:
            self.columns = kwargs.pop("columns")
        if "values" in kwargs:
            self.values = values
        if "padx" in kwargs:
            self.padx = kwargs.pop("padx")
        if "padx" in kwargs:
            self.pady = kwargs.pop("pady")
        
        self.update_values(self.values, **kwargs)
