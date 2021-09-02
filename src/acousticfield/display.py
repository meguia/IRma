import numpy as np
from matplotlib import pyplot as plt
from IPython.display import display, HTML
from .room import find_echoes, find_dir
   
def parsprint(pars, keys=None, cols=None, chan=0):
    '''
    Imprime una tabla en formati HTML a partir del diccionario param con las keys en filas
    y usa como headers de las columnas cols (normalmente se usa 'fc' para esto)
    '''
    if keys is None:
        rtype = list(filter(lambda x: 'rt' in x, pars.keys()))[0]
        keys = ['snr',rtype,'rvalue','edt','c50','c80','ts','dr']
    if cols is None:
        cols = pars['fc']    
    tabla = np.vstack(list(pars[key][:,chan] for key in keys))
    display_table(tabla,cols,keys)    

def echodisplay(data, nechoes, pw=0.7, scale=0.1, wplot=True, fs=48000):
    '''
    Imprime una tabla en formati HTML con los echoes y el directo ordenados
    y si wplot es True grafica espigas en los echoes junto a la RI
    '''
    echoes = find_echoes(data,nechoes,pw,fs=fs)
    keys = [str(n) for n in np.arange(nechoes)]
    cols = ['time (ms)', 'level (dB)', 'distance (m)', 'DIRECT']    
    echoes[:,0] *= 1000
    echoes[:,1] = 10*np.log10(echoes[:,1]/echoes[0,1])
    dist = 0.343*echoes[:,:1]
    direct = np.zeros_like(dist)
    direct[0] = 1
    echoes = np.hstack([echoes, dist, direct])
    echoes = echoes[np.argsort(-echoes[:, 1])]
    display_table(echoes,cols,keys) 
    if (wplot):
        t = 1000*np.arange(len(data))/fs
        fig, ax = plt.subplots(figsize=(18,5))
        ax.plot(t,data,label='RI')
        for n in range(nechoes):
            amp = scale*(echoes[n,1]+20)*np.max(data)
            ax.plot([echoes[n,0],echoes[n,0]],[0,amp],label=str(n))
        ax.legend()
        ax.set_xlabel('Tiempo (ms)')
        ax.set_title('ECHOGRAM')
        ax.set_xlim([0, np.max(echoes[:,0])*1.1])
    return    


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

def irplot(data, fs=48000):
    """ data (nsamples,nchannel) must be a 2D array
    """
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    t = np.arange(nsamples)/fs
    _, ax = plt.subplots(figsize=(18,5))
    for n in range(nchan):
        ndir = find_dir(data[:,n],pw=0.5,fs=fs)
        ax.plot(t,data)
        ax.plot(t[ndir[0]:ndir[1]],data[ndir[0]:ndir[1],n],'r')
    ax.set_xlabel('Time (s)')
    ax.set_title('IMPULSE RESPONSE')

def parsplot(pars, keys, chan=0):
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
                axs[iplot].bar(np.arange(nb)+0.4/nbars*(2*m-nbars+1),pars[pkey][:,chan],width=0.8/nbars)
            axs[iplot].set_xticks(np.arange(nb))
            axs[iplot].set_xticklabels(tuple(pars['fc']))
            axs[iplot].legend(pgraph[n])
            #axs[iplot].ylabel('Tiempo de Reverberacion(s)')
            axs[iplot].set_xlabel('Frequency (Hz)')
            axs[iplot].grid(axis='y')
            #axs[iplot].title('Respuesta Impulso')
            iplot +=1
    return        

def parsdecayplot(pars, chan=0, fs=48000):    
    nb = pars['nbands']
    chan = 0
    nsamples = pars['schr'].shape[2]
    t = np.arange(nsamples)/fs
    ncols = int(np.floor(np.sqrt(nb)))
    nrows = int(np.ceil(nb/ncols))
    fig, axs = plt.subplots(nrows,ncols,figsize=(20,5*nrows))
    for row in range(nrows):
        for col in range(ncols):
            band = row*ncols+col
            if (band<nb):
                axs[row,col].plot(t,pars['schr'][band,chan])
                axs[row,col].plot(pars['tfit'][band,chan],pars['lfit'][band,chan],'r')
                axs[row,col].set_title(pars['fc'][band])
    return            

    
      
    # grafica los modos recibe la salidad de find_modes
    
    # grafica la o las IRS junto con la transferencia como opcion
    
    # graficos comparativos por fuente direccion receptor