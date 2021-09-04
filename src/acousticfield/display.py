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
    keys = [str(n) for n in np.arange(nechoes)]
    cols = ['time (ms)', 'level (dB)', 'distance (m)', 'DIRECT']    
    echoes_multi = find_echoes(data,nechoes,pw,fs=fs)
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nchan = echoes_multi.shape[2]
    for n in range(nchan):
        echoes = echoes_multi[:,:,n]
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
        _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
        if nchan ==1:
            axs = [axs]
        for n in range(nchan):
            echoes = echoes_multi[:,:,n]
            axs[n].plot(t,data[:,n],label='RI')
            for m in range(nechoes):
                amp = scale*(echoes[m,1]+20)*np.max(data)
                axs[n].plot([echoes[m,0],echoes[m,0]],[0,amp],label=str(m))
            axs[n].legend()
            axs[n].set_xlabel('Tiempo (ms)')
            axs[n].set_title('ECHOGRAM Channel ' + str(n))
            axs[n].set_xlim([0, np.max(echoes[:,0])*1.1])
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

def irplot(data, fs=48000, tmax=3.0):
    """ data (nsamples,nchannel) must be a 2D array
    """
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    t = np.arange(nsamples)/fs
    _, axs = plt.subplots(figsize=(18,5*nchan))
    ndir = find_dir(data,pw=0.5,fs=fs)
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        axs[n].plot(t,data[:,n])
        axs[n].plot(t[ndir[0,n]:ndir[1,n]],data[ndir[0,n]:ndir[1,n],n],'r')
        axs[n].set_xlim([0,tmax])
        if n==0:
            axs[n].set_title('IMPULSE RESPONSE')
    axs[n].set_xlabel('Time (s)')        

def irstatplot(data, pstat, fs=48000, tmax=2.0):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    t = np.arange(1,nsamples+1)/fs
    ndir = find_dir(data,pw=0.5,fs=fs)
    _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
    irmax = np.max(np.abs(data))
    kurtmax =  np.nanmax(pstat['kurtosis'])
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        axs[n].semilogx(t,data[:,n]/irmax)
        axs[n].semilogx(t[ndir[0,n]:ndir[1,n]],data[ndir[0,n]:ndir[1,n],n]/irmax,'r',label='direct')
        axs[n].semilogx(pstat['tframe'],pstat['kurtosis'][:,n]/kurtmax,'k',label='kurtosis')
        axs[n].semilogx(pstat['tframe'],pstat['stdexcess'][:,n],'g',label='stdexcess')
        axs[n].semilogx([pstat['mixing'][0,n],pstat['mixing'][0,n]],[-1,1],'k','r')
        axs[n].semilogx([pstat['mixing'][1,n],pstat['mixing'][1,n]],[-1,1],'g','r')
        axs[n].set_xlabel('Time (s)')
        axs[n].set_title('IMPULSE RESPONSE')
        axs[n].set_xlim([0.5*t[ndir[0,n]],tmax])
        axs[n].legend()


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