import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress, kurtosis
from .process import make_filterbank, A_weighting
eps = np.finfo(float).eps

def revtime(ir_input, method='RT20', fs=48000, tmax=3.0):
    '''
    Calcula el tiempo de reverberacion y la integral de Schroeder a partir de la respuesta
    impulso almacenada en ir_input (array numpy o nombre de archivo wav) usando el metodo 'RT30' 'RT20' o 'EDT'
    Lo hace para cada canal del archivo fileir.
    Atencion asume por defecto una decaimiento maximo de 3 segundos (no TR, decaimiento a piso de ruido
    lo cual es un asuncion razonable en la mayor parte de los casos)
    Devuelve por orden: 
    - el (los) tiempos de reverberacion en segundos
    - tiempo incial y final en los que ajusto la recta del decaimiento 
    - nivel inicial y final en dB de la recta del decaimiento (util para el metodo rmax todavia no implementado)
    - integral(es) de Schroeder de toda la respuesta impulso
    '''
    if type(ir_input) is str:
        fs, data = wavfile.read(ir_input + '.wav')
    elif type(ir_input) is np.ndarray:
        data = ir_input
    else:
        raise TypeError('Primer argumento debe ser el array devuelto por extractir o un nombre de archivo')
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nmax = int(min(tmax*fs,nsamples))
    schr = np.zeros((nchan,nmax))
    SNR = np.zeros((nchan,))
    rt = np.zeros((nchan,))
    t12 = np.zeros((nchan,2))
    l12 = np.zeros((nchan,2))
    rvalue = np.zeros((nchan,))
    for n, ir in enumerate(data.T):
        ns = np.mean(ir[nmax:-1][0]**2)
        stemp = np.flip(np.cumsum(ir[::-1]**2)) # integral de Schroeder
        stemp = stemp[:nmax]
        mm = np.arange(nsamples,0,-1)*ns
        n_ns = np.argmax(stemp<mm[:nmax]*np.sqrt(2))
        xv = 10*np.log10(stemp)-10*np.log10(mm[:nmax])
        xv = xv - np.amax(xv)
        tv =  np.arange(nsamples)/fs # array de tiempo
        SNR[n] = -xv[-1] # full range del decaimiento SNR
        schr[n][:nmax] = xv
        if method.lower() == 'RT30' and SNR[n]>35:
            #  Calcula RT usando la definicion del RT30
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-35)
        elif method.lower() == 'RT20' and SNR[n]>25:
            # Idem la definicion del RT20
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-25)
        elif method.lower() == 'RT15' and SNR[n]>20:
            # Idem la definicion del RT20
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-20)
        elif method.lower() == 'EDT' and SNR[n]>10.5:
            # Calculo del decaimiento temprano EDT
            pt1 = np.argmax(xv<-0.5)
            pt2 = np.argmax(xv<-10.5)
        else:
            return rt, t12, l12, schr, SNR, rvalue 
        slope, intercept, r_value, _, _ = linregress(tv[pt1:pt2], xv[pt1:pt2])
        rt[n] = -(intercept + 60)/slope
        t12[n] = tv[[pt1,pt2]]
        l12[n] = intercept+slope*tv[[pt1,pt2]]
        rvalue[n] = r_value    
    return rt, t12, l12, schr, SNR, rvalue 


def clarity(ir_input, fs=48000, tmax = 3.0):
    '''
    Calcula valores de claridad C80 C50 y centro temporal TS a partir de la respuesta impulso ir
    mas adelante deberia tener en cuenta la relacion senal ruido para no sobreestimar la reverberacion
    '''
    if type(ir_input) is str:
        fs, data = wavfile.read(ir_input + '.wav')
    elif type(ir_input) is np.ndarray:
        data = ir_input
    else:
        raise TypeError('Primer argumento debe ser el array devuelto por extractir o un nombre de archivo')
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nmax = int(min(tmax*fs,nsamples))
    ndir = find_dir(data, pw=1.0,fs=fs)
    C80 = np.zeros((nchan,))
    C50 = np.zeros((nchan,))
    TS = np.zeros((nchan,))
    n80 = int(0.08*fs)
    n50 = int(0.05*fs)
    for n, ir in enumerate(data.T):
        e50 = np.sum(np.square(ir[ndir[0,n]:ndir[0,n]+n50]))
        e80 = np.sum(np.square(ir[ndir[0,n]:ndir[0,n]+n80]))
        er = np.sum(np.square(ir[ndir[0,n]:nmax]))
        etr = np.sum(np.multiply((np.arange(ndir[0,n],nmax)-ndir[0,n])/fs,np.square(ir[ndir[0,n]:nmax])))
        C80[n] = 10*np.log10(e80/(er-e80))
        C50[n] = 10*np.log10(e50/(er-e50))
        TS[n] = 1000*etr/er
    return C80, C50, TS    
        

def paracoustic(ir, method='RT20', bankname='fbank', tmax=3.0, fs_default=48000):
    '''
    Calcula los siguientes parametros acusticos POR BANDAS con los nombres de las keys correspondientes
    Reververacion: 'RT30' (o el metodo que se pida), 'EDT'
    Claridad: 'C80', 'C50', 'TS', 
    Relacion senal ruido 'SNR'
    Directo reverberante 'DRR'
    a partir de la respuesta impulso almacenada en ir (array numpy o nombre de archivo wav) 
    Lo hace para cada canal del archivo fileir y para el banco de filtros almacenado en bankname (extension npz)
    devueve un diccionario rev que tiene las siguientes keys: nchan (num canales), nbands (num bandas), fc (frecuencias)
    tr20 (o tr30 o EDT, array de nbands x nchan con los tiempos de reverberancia) tfit, lfit, dchr, lvalues son 
    las salidas de revtime (ver) para cada banda. La banda 0 es wideband (fc = 1)
    '''
    # si bankname es None lo hace wideband
    # dar la opcion de no calcular el filtro A
    try:     
        fbank = np.load(bankname + '.npz')
    except:
        print('Generating new filter bank ')
        try: 
            fs, _ = wavfile.read(ir + '.wav')
        except:
            #raise Exception('Cannot infer sample rate. Please provide wav file or filter bank with specified sample rate')    
            fs = fs_default
        if (len(bankname.split('_')) > 1):
            (noct,bwoct) = [int(ss) for ss in bankname.split('_')[-2:]]
            make_filterbank(noct=noct,bwoct=bwoct,bankname=bankname,fs=fs)
        else:
            make_filterbank(bankname='fbank',fs=fs)    
        fbank = np.load(bankname + '.npz')
    if type(ir) is str:
        fs, data = wavfile.read(ir + '.wav')
        if fs != fbank['fs']:
            raise Exception('Inconsistent sample rate between audio file and filter bank')
    elif type(ir) is np.ndarray:
        data = ir
        fs = fbank['fs']
        print('Using sample rate from filter bank:' + str(fs))
    else:
        raise TypeError('Input must be ndarray or filename')    
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nbands, _, _ = fbank['sos'].shape
    # some stats
    pstat = irstats(data, fs=fs)
    tmixing = np.mean(pstat['mixing'][0,:])
    tnoise = np.mean(pstat['tnoise'][0,:])
    nsamples, nchan = np.shape(data)
    nmax = int(min(tmax*fs,nsamples))
    listofkeys = ['nchan','nbands','fc',method,'EDT','tfit','lfit','schr','rvalue','SNR','C80','C50','TS','DRR']
    pars = dict.fromkeys(listofkeys,0 )
    pars['nchan'] = nchan
    pars['nbands'] = nbands+2
    pars['fc'] = [None]*pars['nbands']
    pars[method] = np.zeros((pars['nbands'],pars['nchan']))
    pars['EDT'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['tfit'] = np.zeros((pars['nbands'],pars['nchan'],2))
    pars['lfit'] = np.zeros((pars['nbands'],pars['nchan'],2))
    pars['schr'] = np.zeros((pars['nbands'],pars['nchan'],nmax))
    pars['rvalue'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['SNR'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['C80'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['C50'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['TS'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['DRR'] = np.zeros((pars['nbands'],pars['nchan']))
    # By Frequency Bands
    ndir = find_dir(data, pw=0.5,fs=fs)
    print(int(tnoise*fs))
    sos_a = A_weighting(fs)
    for n in range(nbands+2):
        if n==nbands:
            pars['fc'][n] = 'A'
            data_filt = signal.sosfiltfilt(sos_a, data/np.amax(np.abs(data)), axis=0)
        elif n>nbands:
            pars['fc'][n] = 'Flat'
            data_filt = data            
        else:    
            pars['fc'][n] = str(int(fbank['fc'][n]))
            data_filt = signal.sosfiltfilt(fbank['sos'][n], data/np.amax(np.abs(data)), axis=0)
        pars['EDT'][n], *_ = revtime(data_filt,'EDT',fs,tmax)
        pars[method][n], pars['tfit'][n], pars['lfit'][n], pars['schr'][n], pars['SNR'][n], pars['rvalue'][n] = revtime(data_filt,method,fs,tmax)
        pars['C80'][n], pars['C50'][n], pars['TS'][n] = clarity(data_filt,fs,tmax)
        pars['DRR'][n] = direct_to_reverb(data_filt,int(tnoise*fs),ndir,fs)
    return pars

def direct_to_reverb(data, nmax, ndir=None, fs=48000):
    nsamples,nchan = data.shape
    nmax = np.minimum(nmax,nsamples)
    if ndir is None:
        ndir = find_dir(data, pw=0.5,fs=fs)
    ddirmax = np.max(np.diff(ndir,axis=0))
    drevmin = nmax-np.max(ndir[1:])
    dirs = [data[ndir[0,n]:ndir[0,n]+ddirmax,n] for n in range(nchan)]
    revs = [data[ndir[1,n]:ndir[1,n]+drevmin,n] for n in range(nchan)]
    EDIR = np.sum(np.square(dirs),axis=1)
    EREV = np.sum(np.square(revs),axis=1)
    return  10.0*np.log10(EDIR/EREV)

def find_dir(data, pw=1.0, fs=48000):
    """ Multichannel
    """
    nw = int(np.floor(pw*fs/1000))
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    _, nchan = np.shape(data)
    ndir = np.zeros((3,nchan),dtype=int)
    # find first local maximum 20 dB below the absolute maximum value
    for n in range(nchan):
        pmax = np.max(np.abs(data[:,n]))
        n0 = np.argmax(np.abs(data[:,n])>pmax/10)
        n0=max(n0,nw+1) 
        npk = np.argmax(np.abs(data[n0-nw:n0+nw,n]))
        nc = n0+npk-nw-2
        ndir[0,n] = np.maximum(1,int(nc-1.0*nw))
        ndir[1,n] = int(nc+1.5*nw)
        ndir[2,n] = nc
    return ndir

def find_echoes(data, nechoes=10, pw=1.0, fs=48000):
    nw = int(np.floor(0.5*pw*fs/1000))
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    _, nchan = np.shape(data)
    echoes = np.zeros((nechoes,2,nchan))
    amp = 1-np.exp(-np.square(np.linspace(-3.0,3.0,6*nw)))
    data_copy = np.copy(data)
    for n in range(nchan):
        for m in range(nechoes):
            n0 = np.argmax(np.abs(data_copy[:,n]))
            echoes[m,0,n] = n0/fs
            echoes[m,1,n] = np.mean(np.square(data[n0-nw:n0+nw,n]))
            data_copy[n0-3*nw:n0+3*nw,n] *= amp
    return echoes

def irstats(ir, window=0.01, overlap=0.005, fs=48000):
    if type(ir) is str:
        fs, data = wavfile.read(ir + '.wav')
    elif type(ir) is np.ndarray:
        data = ir
    else:
        raise TypeError('Input must be ndarray or filename')    
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    kurt_confidence = 0.5
    excess_confidence = 0.9
    stdbup_confidence = 1.0
    ndir = find_dir(data, fs=fs)
    nsamples, nchan = np.shape(data)
    listofkeys = ['chan','tframe','std','kurtosis','stdexcess','stdbup']
    pars = dict.fromkeys(listofkeys,0 )
    pars['nchan'] = nchan
    nwindow = int(window*fs)
    noverlap = int(overlap*fs)
    nframes = int(np.floor((nsamples-noverlap)/(nwindow-noverlap)))
    frames = [[(nwindow-noverlap)*n,(nwindow-noverlap)*n+nwindow] for n in range(nframes)]
    pars['tframe'] = np.zeros((nframes,1))
    pars['std'] = np.zeros((nframes,nchan))
    pars['kurtosis'] = np.zeros((nframes,nchan))
    pars['stdexcess'] = np.zeros((nframes,nchan))
    pars['stdbup'] = np.zeros((nframes,nchan))
    pars['mixing'] = np.zeros((2,nchan))
    pars['tnoise'] = np.zeros((1,nchan))
    for m in range(nframes):
        fr = data[frames[m][0]:frames[m][1],:]
        pars['tframe'][m] = np.mean(frames[m])/fs
        av = np.mean(fr,axis=0)
        isdir = np.full((nchan,),np.nan)
        isdir[frames[m][1] > ndir[0,:]] = 1
        temp = np.std(fr,axis=0) * isdir
        if np.any(np.isnan(temp)):
            pars['std'][m] = np.zeros((1,nchan))   
        else:
            pars['std'][m] = temp
        pars['kurtosis'][m] = kurtosis(fr,axis=0) * isdir
        pars['stdexcess'][m] = np.mean(np.abs(fr-av)>pars['std'][m],axis=0)*3.0*isdir
    nmix = np.argmax(pars['kurtosis']<kurt_confidence,axis=0)    
    pars['mixing'][0,:] = pars['tframe'][nmix][:,0]
    nmix = np.argmax(pars['stdexcess']>excess_confidence,axis=0)
    pars['mixing'][1,:] = pars['tframe'][nmix][:,0]
    for n in range(nchan):
        stdb = signal.savgol_filter(10*np.log10(pars['std'][:,0]),51,3,axis=0)
        pars['stdbup'][:,n] = stdb-np.nanmin(stdb)
    nnoise = np.argmax(pars['stdbup']<stdbup_confidence,axis=0)    
    pars['tnoise'][0,:] = pars['tframe'][nnoise][:,0]
    return pars    

# echo density 
#     
#def find_modes # encuentra modos hasta una frecuencia

#def binaural # aca va ITD ILD e intensidad binaural IACC

#def sti # inteligilibilidad del habla

#def spatial # fraccion de energia lateral




