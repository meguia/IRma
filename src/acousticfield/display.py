import numpy as np
import sounddevice as sd
import pandas as pd
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from matplotlib import pyplot as plt
from IPython.display import display, HTML
   
def printable(param, keys, cols):
    '''
    Imprime una tabla en formati HTML a partir del diccionario param con las keys en filas
    y usa como headers de las columnas cols (normalmente se usa 'fc' para esto)
    '''
    tabla = np.vstack(list(param[key][:,0] for key in keys))
    display_table(tabla,cols,keys)    
    
def display_table(data,headers,rownames):
    html = "<table class='table table-stripped'>"
    html += "<tr>"
    html += "<td><h4></h4><td>"
    for header in headers:
        html += "<td><h4>%s</h4><td>"%(header)
    html += "</tr>" 
    for n,row in enumerate(data):
        html += "<tr>"
        if rownames is not None:
            html += "<td><h4>%s</h4><td>"%(rownames[n].upper())
        else:
            html += "<td><h4>%s</h4><td>"%(str(n+1))
        for field in row:
            html += "<td>%.3f<td>"%(field)
        html += "</tr>"
    html += "</table>"
    display(HTML(html)) 

    # funciones para graficar de formas diversas y bonitas
    
    # espectrograma
    
    # graficar decaimientos de schroeder
    
    # graficar claridad y rever como barras o lineas
      
    # grafica los modos recibe la salidad de find_modes
    
    # grafica la o las IRS junto con la transferencia como opcion
    
    # graficos comparativos por fuente direccion receptor