import numpy as np
from matplotlib import pyplot as plt
from IPython.display import display, HTML
from .room import find_echoes, find_dir, irstats
from .process import spectrum, spectrogram, fconvolve
plt.style.use('dark_background')
   
def pars_print(pars, keys=None, cols=None, chan=1):
    '''
    Imprime una tabla en formati HTML a partir del diccionario param con las keys en filas
    y usa como headers de las columnas cols (normalmente se usa 'fc' para esto)
    '''
    if keys is None:
        rtype = list(filter(lambda x: 'rt' in x, pars.keys()))[0]
        keys = ['snr',rtype,'rvalue','edt','c50','c80','ts','dr']
    if cols is None:
        cols = pars['fc']    
    tabla = np.vstack(list(pars[key][:,chan-1] for key in keys))
    display_table(tabla,cols,keys)    

def echo_display(data, nechoes, pw=0.7, scale=0.1, wplot=True, fs=48000):
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
            axs[n].set_xlim([0.7*echoes[0,0], np.max(echoes[:,0])*1.1])
    return echoes_multi  


def display_table(data,headers,rownames):
    html = "<table class='table-condensed'>"
    html += "<tr>"
    html += "<td><h4>Band</h4><td>"
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

def ir_plot(data, fs=48000, tmax=3.0):
    """ data (nsamples,nchannel) must be a 2D array
    """
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    t = np.arange(nsamples)/fs
    _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
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
    return    

def irstat_plot(data, window=0.01, overlap=0.002, fs=48000, logscale=True, tmax=2.0):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    pstat = irstats(data, window=window, overlap=overlap, fs=fs)
    nsamples, nchan = np.shape(data)
    t = np.arange(1,nsamples+1)/fs
    ndir = find_dir(data,pw=0.5,fs=fs)
    _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
    irmax = np.max(np.abs(data))
    kurtmax =  np.nanmax(pstat['kurtosis'])
    stdbupmax =  np.nanmax(pstat['stdbup'])
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        axs[n].plot(t,data[:,n]/irmax)
        axs[n].plot(t[ndir[0,n]:ndir[1,n]],data[ndir[0,n]:ndir[1,n],n]/irmax,'r',label='direct')
        axs[n].plot(pstat['tframe'],pstat['kurtosis'][:,n]/kurtmax,'w',label='kurtosis')
        axs[n].plot(pstat['tframe'],pstat['stdexcess'][:,n],'y',label='stdexcess')
        axs[n].plot(pstat['tframe'],pstat['stdbup'][:,n]/stdbupmax,'c',label='stdbup')
        axs[n].plot([pstat['mixing'][0,n],pstat['mixing'][0,n]],[-1,1],'w')
        axs[n].plot([pstat['mixing'][1,n],pstat['mixing'][1,n]],[-1,1],'y')
        axs[n].plot([pstat['tnoise'][0,n],pstat['tnoise'][0,n]],[-1,1],'c')
        if logscale:
            axs[n].set_xscale('log')
        axs[n].set_xlabel('Time (s)')
        axs[n].set_xlim([0.5*t[ndir[0,n]],tmax])
        axs[n].legend()
        if n==0:
            axs[n].set_title('IMPULSE RESPONSE (Mixing Time)')
    axs[n].set_xlabel('Time (s)')
    return pstat

def acorr_plot(data, trange=0.2, fs=48000):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = data.shape
    acorr = fconvolve(data[::-1],data)
    _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
    nrange = int(trange*fs)
    t = np.linspace(-trange,trange,2*nrange+1)
    acorr_range=acorr[nsamples-nrange:nsamples+nrange+1,:]
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        axs[n].plot(t*1000,acorr_range[:,n])
        axs[n].set_xlim([-trange*1000,trange*1000])
        if n==0:
            axs[n].set_title('IR AUTOCORRELATION')
    axs[n].set_xlabel('Time (ms)')
    return acorr

def spectrum_plot(data, logscale=False, fmax=12000, fs=48000, lrange=60, overlay=False):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    _, nchan = data.shape
    sp = spectrum(data, fs=fs)
    if overlay:
        _, axs = plt.subplots(1,1,figsize=(18,6))
    else:    
        _, axs = plt.subplots(nchan,1,figsize=(18,5*nchan))
    nmax = np.argmax(sp['f']>fmax)
    smax = np.max(sp['s'][:,:nmax])
    smin = smax-lrange
    for n in range(nchan):
        if overlay or nchan==1:
            ax = axs
        else:    
            ax = axs[n]
        if logscale:
            ax.semilogx(sp['f'],sp['s'][n],label=str(n))
            ax.set_xlim([10,fmax])
        else:
            ax.plot(sp['f'],sp['s'][n],label=str(n))
            ax.set_xlim([0,fmax])
        ax.set_ylim([smin,smax])    
        if n==0:
            ax.set_title('POWER SPECTRAL DENSITY')
    ax.set_xlabel('Frequency (Hz)')
    ax.legend()
    return sp

def spectrogram_plot(data,window,overlap,fs,chan=0,fmax=22000,tmax=2.0,normalized=False,logf=False,lrange=60):
    kwargs = {'windowSize': window,'overlap': overlap,'fs': fs, 'windowType': 'hanning',
          'normalized': normalized, 'logf': logf}
    spec = spectrogram(data[:,chan], **kwargs )
    maxlevel = 10*np.log10(np.max(spec['s']))
    levels = np.linspace(maxlevel-lrange,maxlevel,50)
    fig, ax = plt.subplots(figsize=(20,12))
    ctr = ax.contourf(spec['t'],spec['f'],10*np.log10(spec['s'][0,:,:]),levels)
    ax.set_xlim([spec['t'][0],tmax])
    ax.set_ylim([0,fmax])
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    fig.colorbar(ctr)
    return spec

def pars_plot(pars, keys, chan=1):
    # busca la ocurrencia de 'rt' 'edt' 'snr' 'c80' 'c50' 'ts' 'dr' en keys
    rtype = list(filter(lambda x: 'rt' in x, pars.keys()))
    pgraph = [['snr'],[rtype[0],'edt'],['c50','c80'],['ts'],['dr']]
    isplot = []
    for pl in pgraph:
        isplot.append(np.any([p in keys for p in pl]))
    nplot = np.sum(isplot)
    ylabels = ['Signal/Noise (dB)','Reverberation Time (s)','Clarity (dB)','Center Time (ms)','Direct/Reverberant (dB)']
    fig, axs = plt.subplots(nplot,1,figsize=(18,5*nplot))
    iplot = 0
    nb = len(pars['fc'])
    for n in range(5):
        if isplot[n]:
            nbars = len(pgraph[n])
            for m,pkey in enumerate(pgraph[n]):
                axs[iplot].bar(np.arange(nb)+0.4/nbars*(2*m-nbars+1),pars[pkey][:,chan-1],width=0.8/nbars)
            axs[iplot].set_xticks(np.arange(nb))
            axs[iplot].set_xticklabels(tuple(pars['fc']))
            axs[iplot].legend(pgraph[n])
            axs[iplot].set_xlabel('Frequency (Hz)')
            axs[iplot].grid(axis='y')
            axs[iplot].set_ylabel(ylabels[n])
            iplot +=1
    return        

def parsdecay_plot(pars, chan=1, fs=48000):    
    nb = pars['nbands']
    nsamples = pars['schr'].shape[2]
    t = np.arange(nsamples)/fs
    ncols = int(np.floor(np.sqrt(nb)))
    nrows = int(np.ceil(nb/ncols))
    fig, axs = plt.subplots(nrows,ncols,figsize=(20,5*nrows))
    for row in range(nrows):
        for col in range(ncols):
            band = row*ncols+col
            if (band<nb):
                axs[row,col].plot(t,pars['schr'][band,chan-1])
                axs[row,col].plot(pars['tfit'][band,chan-1],pars['lfit'][band,chan-1],'r')
                axs[row,col].set_title(pars['fc'][band])
    return            

    
      
    # grafica los modos recibe la salidad de find_modes
    
    # grafica la o las IRS junto con la transferencia como opcion
    
    # graficos comparativos por fuente direccion receptor