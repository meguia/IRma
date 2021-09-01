import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from process import make_filterbank
from process import A_weighting

def revtime(ir_input, method='rt20', fs=48000, tmax=3.0):
    '''
    Calcula el tiempo de reverberacion y la integral de Schroeder a partir de la respuesta
    impulso almacenada en ir_input (array numpy o nombre de archivo wav) usando el metodo 'rt30' 'rt20' o 'edt'
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
    snr = np.zeros((nchan,))
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
        snr[n] = -xv[-1] # full range del decaimiento SNR
        if method.lower() == 'rt30' and snr[n]>35:
            #  Calcula RT usando la definicion del RT30
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-35)
        elif method.lower() == 'rt20' and snr[n]>25:
            # Idem la definicion del RT20
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-25)
        elif method.lower() == 'rt15' and snr[n]>20:
            # Idem la definicion del RT20
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-20)
        elif method.lower() == 'edt' and snr[n]>10.5:
            # Calculo del decaimiento temprano EDT
            pt1 = np.argmax(xv<-0.5)
            pt2 = np.argmax(xv<-10.5)
        else:
            break
        slope, intercept, r_value, p_value, std_err = linregress(tv[pt1:pt2], xv[pt1:pt2])
        rt[n] = -(intercept + 60)/slope
        t12[n] = tv[[pt1,pt2]]
        l12[n] = intercept+slope*tv[[pt1,pt2]]
        schr[n][:nmax] = xv
        rvalue[n] = r_value    
    return rt, t12, l12, schr, snr, rvalue  


def clarity(ir_input, fs=48000, tmax = 3.0):
    '''
    Calcula valores de claridad C80 C50 y centro temporal ts a partir de la respuesta impulso ir
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
    c80 = np.zeros((nchan,))
    c50 = np.zeros((nchan,))
    ts = np.zeros((nchan,))
    n80 = int(0.08*fs)
    n50 = int(0.05*fs)
    for n, ir in enumerate(data.T):
        e50 = np.sum(np.square(ir[:n50]))
        e80 = np.sum(np.square(ir[:n80]))
        er = np.sum(np.square(ir[:nmax]))
        etr = np.sum(np.multiply(np.arange(nmax)/fs,np.square(ir[:nmax])))
        c80[n] = 10*np.log10(e80/(er-e80))
        c50[n] = 10*np.log10(e50/(er-e50))
        ts[n] = etr/er
    return c80, c50, ts    
        

def time_based(ir, method='rt20', bankname=None, tmax=3.0):
    '''
    Calcula los siguientes parametros acusticos POR BANDAS con los nombres de las keys correspondientes
    Reververacion: 'rt30' (o el metodo que se pida), 'edt'
    Claridad: 'c80', 'c50', 'ts', 
    Relacion senal ruido 'snr'
    a partir de la respuesta impulso almacenada en ir (array numpy o nombre de archivo wav) 
    Lo hace para cada canal del archivo fileir y para el banco de filtros almacenado en bankname (extension npz)
    devueve un diccionario rev que tiene las siguientes keys: nchan (num canales), nbands (num bandas), fc (frecuencias)
    tr20 (o tr30 o edt, array de nbands x nchan con los tiempos de reverberancia) tfit, lfit, dchr, lvalues son 
    las salidas de revtime (ver) para cada banda. La banda 0 es wideband (fc = 1)
    '''
    # si bankname es None lo hace wideband
    # dar la opcion de no calcular el filtro A
    try:     
        fbank = np.load(bankname + '.npz')
    except:
        make_filterbank(bankname='fbank')
        fbank = np.load(bankname + '.npz')
    if type(ir) is str:
        fs, data = wavfile.read(ir + '.wav')
        if fs != fbank['fs']:
            raise Exception('frecuencia de sampleo inconsistente')
    elif type(ir) is np.ndarray:
        data = ir
        fs = fbank['fs']
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nbands, _, _ = fbank['sos'].shape
    nsamples, nchan = np.shape(data)
    nmax = int(min(tmax*fs,nsamples))
    listofkeys = ['nchan','nbands','fc',method,'edt','tfit','lfit','schr','rvalue','snr','c80','c50','ts','dr']
    rev = dict.fromkeys(listofkeys,0 )
    rev['nchan'] = nchan
    rev['nbands'] = nbands+2
    rev['fc'] = [None]*rev['nbands']
    rev[method] = np.zeros((rev['nbands'],rev['nchan']))
    rev['edt'] = np.zeros((rev['nbands'],rev['nchan']))
    rev['tfit'] = np.zeros((rev['nbands'],rev['nchan'],2))
    rev['lfit'] = np.zeros((rev['nbands'],rev['nchan'],2))
    rev['schr'] = np.zeros((rev['nbands'],rev['nchan'],nmax))
    rev['rvalue'] = np.zeros((rev['nbands'],rev['nchan']))
    rev['snr'] = np.zeros((rev['nbands'],rev['nchan']))
    rev['c80'] = np.zeros((rev['nbands'],rev['nchan']))
    rev['c50'] = np.zeros((rev['nbands'],rev['nchan']))
    rev['ts'] = np.zeros((rev['nbands'],rev['nchan']))
    # Por Bandas de frecuencia primero
    for n in range(nbands):
        rev['fc'][n] = str(int(fbank['fc'][n]))
        data_filt = signal.sosfiltfilt(fbank['sos'][n], data/np.amax(np.abs(data)), axis=0)
        rev['edt'][n], _ = revtime(data_filt,'edt',fs,tmax)
        rev[method][n], rev['tfit'][n], rev['lfit'][n], rev['schr'][n], rev['snr'][n], rev['rvalue'][n] = revtime(data_filt,method,fs,tmax)
        rev['c80'][n], rev['c50'][n], rev['ts'][n] = clarity(data_filt,fs,tmax)
        rev['dr'][n] = direct_to_reverb(data_filt,fs)
    # Aplicando el filtro tipo A
    sos_a = A_weighting(fs)
    data_filt = signal.sosfiltfilt(sos_a, data/np.amax(np.abs(data)), axis=0)
    rev['fc'][10] = 'A'
    rev['edt'][10], _ = revtime(data_filt,'edt',fs,tmax)
    rev[method][10], rev['tfit'][10], rev['lfit'][10], rev['schr'][10], rev['snr'][10], rev['rvalue'][10] = revtime(data_filt,method,fs,tmax)
    rev['c80'][10], rev['c50'][10], rev['ts'][10] = clarity(data_filt,fs,tmax)
    rev['dr'][10] = direct_to_reverb(data_filt,fs)
    # Sin modificar (Flat)
    rev['fc'][11] = 'Flat'
    rev['edt'][11], _ = revtime(data,'edt',fs,tmax)
    rev[method][11], rev['tfit'][11], rev['lfit'][11], rev['schr'][11], rev['snr'][11], rev['rvalue'][11] = revtime(data,method,fs,tmax)
    rev['c80'][11], rev['c50'][11], rev['ts'][11] = clarity(data,fs,tmax)
    rev['dr'][11] = direct_to_reverb(data,fs)
    return rev

def direct_to_reverb(data, fs=48000):
    ndir = find_dir(data, pw=0.5,fs=fs)
    EDIR = np.sum(np.square(data[ndir[0]:ndir[1]]))
    EREV = np.sum(np.square(data[ndir[1]+1:]))
    return 10.0*np.log10(EDIR/EREV)

def find_dir(data, pw=1.0, fs=48000):
    nw = int(np.floor(pw*fs/1000))
    pmax = np.max(np.abs(data))
    n0 = np.argmax(np.abs(data)>pmax/np.sqrt(10))
    n0=max(n0,nw+1) 
    npk = np.argmax(np.abs(data[n0-nw:n0+nw]))
    nc = n0+npk-nw-2
    n1 = np.maximum(1,int(nc-1.0*nw))
    n2 = int(nc+1.5*nw)
    return [n1,n2]

def find_echoes(data, nechoes=10, pw=1.0, fs=48000):
    nw = int(np.floor(0.5*pw*fs/1000))
    echoes = np.empty((nechoes,2))
    data_copy = np.copy(data)
    for n in range(nechoes):
        n0 = np.argmax(np.abs(data_copy))
        echoes[n,0] = n0/fs
        echoes[n,1] = np.sum(np.square(data[n0-nw:n0+nw]))
        data_copy[n0-nw:n0+nw] *= 0.05
    return echoes  

#echo sorting and echo density

#def find_modes # encuentra modos hasta una frecuencia

#def binaural # aca va ITD ILD e intensidad binaural IACC

#def sti # inteligilibilidad del habla

#def spatial # fraccion de energia lateral




