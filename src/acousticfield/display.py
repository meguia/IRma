import numpy as np
import sounddevice as sd
import pandas as pd
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from matplotlib import pyplot as plt
from IPython.display import display, HTML
   
def printable(pars, keys=None, cols=None):
    '''
    Imprime una tabla en formati HTML a partir del diccionario param con las keys en filas
    y usa como headers de las columnas cols (normalmente se usa 'fc' para esto)
    '''
    if keys is None:
        rtype = list(filter(lambda x: 'rt' in x, pars.keys()))[0]
        keys = ['snr',rtype,'edt','c50','c80','ts','dr']
    if cols is None:
        cols = pars['fc']    
    tabla = np.vstack(list(pars[key][:,0] for key in keys))
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

def parsplot(pars, keys):
    # busca la ocurrencia de 'rt' 'edt' 'snr' 'c80' 'c50' 'ts' 'dr' en keys
    rtype = list(filter(lambda x: 'rt' in x, pars.keys()))
    pgraph = [['snr'],[rtype[0],'edt'],['c50','c80'],['ts'],['dr']]
    isplot = []
    for pl in pgraph:
        isplot.append(np.any([p in keys for p in pl]))
    nplot = np.sum(isplot)    
    fig, axs = plt.subplots(nplot,1,figsize=(18,5*nplot))
    iplot = 0
    nb = len(pars['fc'])
    for n in range(5):
        if isplot[n]:
            nbars = len(pgraph[n])
            for m,pkey in enumerate(pgraph[n]):
                axs[iplot].bar(np.arange(nb)+0.4/nbars*(2*m-nbars+1),pars[pkey][:,0],width=0.8/nbars)
            axs[iplot].set_xticks(np.arange(nb))
            axs[iplot].set_xticklabels(tuple(pars['fc']))
            axs[iplot].legend(pgraph[n])
            #axs[iplot].ylabel('Tiempo de Reverberacion(s)')
            axs[iplot].set_xlabel('Frecuencia (Hz)')
            axs[iplot].grid(axis='y')
            #axs[iplot].title('Respuesta Impulso')
            iplot +=1
    return        
    
    # espectrograma
    
    # graficar decaimientos de schroeder
    
    # graficar claridad y rever como barras o lineas
      
    # grafica los modos recibe la salidad de find_modes
    
    # grafica la o las IRS junto con la transferencia como opcion
    
    # graficos comparativos por fuente direccion receptor