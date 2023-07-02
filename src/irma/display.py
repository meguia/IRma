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
        rtype = list(filter(lambda x: 'RT' in x, pars.keys()))[0]
        keys = ['SNR',rtype,'rvalue','EDT','C50','C80','TS','DRR']
    if cols is None:
        cols = pars['fc']    
    tabla = np.vstack(list(pars[key][:,chan-1] for key in keys))
    display_table(tabla,cols,keys)    

def echo_display(data, nechoes, pw=0.7, scale=0.1, wplot=True, table=True, fs=48000, labels=None, axs=None,redraw=True):
    '''
    Imprime una tabla en formati HTML con los echoes y el directo ordenados
    y si wplot es True grafica espigas en los echoes junto a la RI
    '''
    keys = [str(n) for n in np.arange(nechoes)]
    cols = ['time (ms)', 'level (dB)', 'distance (m)', 'DIRECT']    
    echoes_multi = find_echoes(data,nechoes,pw,fs=fs)
    print(echoes_multi)
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nchan = echoes_multi.shape[2]
    if labels is None:
        labels = ['Ch ' + str(n) for n in range(nchan)]
    for n in range(nchan):
        echoes = echoes_multi[:,:,n]
        echoes[:,0] *= 1000
        echoes[:,1] = 10*np.log10(echoes[:,1]/echoes[0,1])
        dist = 0.343*echoes[:,:1]
        direct = np.zeros_like(dist)
        direct[0] = 1
        echoes = np.hstack([echoes, dist, direct])
        echoes = echoes[np.argsort(-echoes[:, 1])]
        if table:
            display_table(echoes,cols,keys) 
    if (wplot):
        t = 1000*np.arange(len(data))/fs
        if axs is None:    
            _, axs = plt.subplots(nchan,1,figsize=(18,3*nchan))
        if nchan ==1:
            axs = [axs]
        for n in range(nchan):
            if redraw:
                axs[n].clear()
            echoes = echoes_multi[:,:,n]
            axs[n].plot(t,data[:,n],label=labels[n])
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

def ir_plot(data, fs=48000, tmax=3.0, labels=None, figsize=None, redraw=True, axs=None):
    """ data (nsamples,nchannel) must be a 2D array
    """
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    t = np.arange(nsamples)/fs
    if figsize is None:
        figsize = (18,3*nchan)
    if axs is None:    
        _, axs = plt.subplots(nchan,1,figsize=figsize)
    ndir = find_dir(data,pw=0.5,fs=fs)
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        if redraw:
            axs[n].clear()
        if labels is not None:
            axs[n].plot(t,data[:,n],label=labels[n])
            axs[n].legend()
        else:
            axs[n].plot(t,data[:,n])
        axs[n].plot(t[ndir[0,n]:ndir[1,n]],data[ndir[0,n]:ndir[1,n],n],'r')
        axs[n].set_xlim([0,tmax])    
        if n==0:
            axs[n].set_title('IMPULSE RESPONSE')  
    axs[n].set_xlabel('Time (s)')
    return axs


def irstat_plot(data, window=0.01, overlap=0.002, fs=48000, logscale=True, tmax=2.0, axs = None):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    pstat = irstats(data, window=window, overlap=overlap, fs=fs)
    nsamples, nchan = np.shape(data)
    t = np.arange(1,nsamples+1)/fs
    ndir = find_dir(data,pw=0.5,fs=fs)
    if axs is None:
        _, axs = plt.subplots(nchan,1,figsize=(18,3*nchan))
    irmax = np.max(np.abs(data))
    kurtmax =  np.nanmax(pstat['kurtosis'])
    stdbupmax =  np.nanmax(pstat['stdbup'])
    if nchan==1:
        axs = [axs]
    for n in range(nchan):
        axs[n].clear()
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
    return axs


def acorr_plot(data, trange=0.2, fs=48000):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = data.shape
    acorr = fconvolve(data[::-1],data)
    fig, axs = plt.subplots(nchan,1,figsize=(18,3*nchan))
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
    return axs, fig

def spectrum_plot(data, logscale=False, fmax=12000, fs=48000, lrange=60, figsize=None, overlay=True, axs=None, labels=None):
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    _, nchan = data.shape
    sp = spectrum(data, fs=fs)
    if figsize is None:
        figsize = (18,3*nchan)
    if axs is None:    
        _, axs = plt.subplots(nchan,1,figsize=figsize)  
    nmax = np.argmax(sp['f']>fmax)
    smax = np.max(sp['s'][:,:nmax])
    smin = smax-lrange
    if nchan==1:
        axs = [axs]
    if labels is None:
        labels = ['Ch ' + str(n) for n in range(nchan)]
    for n in range(nchan):
        if not overlay:
            axs[n].clear()
        if logscale:
            axs[n].semilogx(sp['f'],sp['s'][n],label=labels[n])
            axs[n].set_xlim([10,fmax])
        else:
            axs[n].plot(sp['f'],sp['s'][n],label=labels[n])
            axs[n].set_xlim([0,fmax])
        axs[n].set_ylim([smin,smax])    
        axs[n].grid()
        if n==0:
            axs[n].set_title('TRANSFER FUNCTION')
    axs[n].set_xlabel('Frequency (Hz)')
    axs[n].legend()
    return axs



def spectrogram_plot(data,window,overlap,fs,chan=0,fmax=22000,tmax=2.0,normalized=False,logf=False,lrange=60):
    kwargs = {'windowSize': window,'overlap': overlap,'fs': fs, 'windowType': 'hanning',
          'normalized': normalized, 'logf': logf}
    spec = spectrogram(data[:,chan], **kwargs )
    maxlevel = 10*np.log10(np.max(spec['s']))
    levels = np.linspace(maxlevel-lrange,maxlevel,50)
    fig, ax = plt.subplots(figsize=(20,8))
    ctr = ax.contourf(spec['t'],spec['f'],10*np.log10(spec['s'][0,:,:]),levels)
    ax.set_xlim([spec['t'][0],tmax])
    ax.set_ylim([0,fmax])
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Frequency (Hz)')
    fig.colorbar(ctr)
    return ax, fig

def pars_plot(pars, keys, chan=1):
    # busca la ocurrencia de 'RT' 'EDT' 'SNR' 'C80' 'C50' 'TS' 'DRR' en keys
    rtype = list(filter(lambda x: 'rt' in x, pars.keys()))
    pgraph = [['SNR'],[rtype[0],'EDT'],['C50','C80'],['TS'],['DRR']]
    isplot = []
    for pl in pgraph:
        isplot.append(np.any([p in keys for p in pl]))
    nplot = np.sum(isplot)
    ylabels = [
        'Signal/Noise (dB)',
        'Reverberation Time (s)',
        'Clarity (dB)',
        'Center Time (ms)',
        'Direct/Reverberant (dB)'
    ]
    fig, axs = plt.subplots(nplot,1,figsize=(18,3*nplot))
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
    return axs, fig


def pars_plot_compared(pars, keys, chans=[1],labels=None,title=None,axs=None):
    # busca la ocurrencia de 'RT' 'EDT' 'SNR' 'C80' 'C50' 'TS' 'DRR' en keys
    rtype = list(filter(lambda x: 'rt' in x, pars.keys()))
    pgraph = ['SNR',rtype[0],'EDT','C50','C80','TS','DRR']
    isplot = []
    for pl in pgraph:
        isplot.append(pl in keys)
    nplot = np.sum(isplot)
    ylabels = [
        'Signal/Noise (dB)',
        'Reverberation Time (s)',
        'Early Decay Time (s)',
        'Clarity (dB)',
        'Clarity (dB)',
        'Center Time (ms)',
        'Direct/Reverberant (dB)'
    ]
    if axs is None:
        _, axs = plt.subplots(nplot,1,figsize=(18,3*nplot))
    iplot = 0
    nb = len(pars['fc'])
    if nplot==1:
        axs = [axs]
    for n in range(7):
        if isplot[n]:
            nbars = len(chans)
            axs[iplot].clear()
            for c in chans:
              axs[iplot].bar(np.arange(nb)+0.4/nbars*(2*c-nbars),pars[pgraph[n]][:,c-1],width=0.8/nbars)
            axs[iplot].set_xticks(np.arange(nb))
            axs[iplot].set_xticklabels(tuple(pars['fc']))
            if labels is not None:
              axs[iplot].legend(labels)
            else:  
              axs[iplot].legend(chans)
            axs[iplot].set_xlabel('Frequency (Hz)')
            axs[iplot].grid(axis='y')
            axs[iplot].set_ylabel(ylabels[n])
            if iplot==0 and title is not None:
              axs[iplot].set_title(title)  
            iplot +=1
    return axs

def pars_compared_axes(pars, key, axs, chans=None,labels=None,title=None,redraw=True):
    # busca la ocurrencia de 'SNR' 'RT' 'EDT' 'C80' 'C50' 'TS' 'DRR' en keys[:2]
    idx = ['SN','RT','ED','C5','C8','TS','DR'].index(key[:2])
    ylabels = [
        'Signal/Noise (dB)',
        'Reverberation Time (s)',
        'Early Decay Time (s)',
        'Clarity (dB)',
        'Clarity (dB)',
        'Center Time (ms)',
        'Direct/Reverberant (dB)'
    ]
    if chans is None:
        chans = np.arange(pars[key].shape[1]) + 1 
    nb = len(pars['fc'])
    nbars = len(chans)
    if redraw:
        axs.clear()
    for c in chans:
        axs.bar(np.arange(nb)+0.4/nbars*(2*c-nbars),pars[key][:,c-1],width=0.8/nbars)
    axs.set_xticks(np.arange(nb))
    axs.set_xticklabels(tuple(pars['fc']))
    if labels is not None:
        axs.legend(labels)
    else:  
        axs.legend(chans)
    axs.set_xlabel('Frequency (Hz)')
    axs.grid(axis='y')
    axs.set_ylabel(ylabels[idx])
    if title is not None:
        axs.set_title(title)  
    return



def parsdecay_plot(pars, chan=1, fs=48000):    
    nb = pars['nbands']
    nsamples = pars['schr'].shape[2]
    t = np.arange(nsamples)/fs
    ncols = int(np.floor(np.sqrt(nb)))
    nrows = int(np.ceil(nb/ncols))
    fig, axs = plt.subplots(nrows,ncols,figsize=(20,3*nrows))
    for row in range(nrows):
        for col in range(ncols):
            band = row*ncols+col
            if (band<nb):
                axs[row,col].plot(t,pars['schr'][band,chan-1])
                axs[row,col].plot(pars['tfit'][band,chan-1],pars['lfit'][band,chan-1],'r')
                axs[row,col].set_title(pars['fc'][band])
    return axs, fig            

    
def transfer_plot(data,f=None,logscale=False, fmax=6000, fmin=60,fs=48000, lrange=60, overlay=True):
    if type(data) == dict:
        f = data['f']
        H = data['H']
    else:
        H = data
    if H.ndim == 1:
        H = H[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = H.shape
    if f is None:
        f = np.linspace(0,fs/2,nsamples)    
    if overlay or nchan==1:
        fig, axs = plt.subplots(2,1,figsize=(18,6))
    else:    
        fig, axs = plt.subplots(2*nchan,1,figsize=(18,3*nchan))
    nmax = np.argmax(f>fmax)
    nmin = np.argmax(f>fmin)
    H = H[nmin:nmax]
    f = f[nmin:nmax]
    HdB = 20*np.log10(np.abs(H))
    smax = np.max(HdB)
    smin = smax-lrange
    for n in range(nchan):
        ax1 = axs[2*n]
        ax2 = axs[2*n+1]
        if logscale:
            ax1.semilogx(f,HdB[:,n],label=str(n))
            ax2.semilogx(f,np.unwrap(np.angle(H[:,n])),label=str(n))
        else:
            ax1.plot(f,HdB[:,n],label=str(n))
            ax2.plot(f,np.unwrap(np.angle(H[:,n])),label=str(n))  
        ax1.set_ylim([smin,smax])
        ax1.legend()
        ax2.legend() 
        if n==0:
            ax1.set_title('Transfer Power')
    ax2.set_xlabel('Frequency (Hz)')
    return axs, fig



    # grafica los modos recibe la salidad de find_modes
    
    # grafica la o las IRS junto con la transferencia como opcion
    
    # graficos comparativos por fuente direccion receptor
