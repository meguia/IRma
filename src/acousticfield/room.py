import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from .process import make_filterbank
from .process import A_weighting

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
        

def paracoustic(ir, method='rt20', bankname='fbank', tmax=3.0):
    '''
    Calcula los siguientes parametros acusticos POR BANDAS con los nombres de las keys correspondientes
    Reververacion: 'rt30' (o el metodo que se pida), 'edt'
    Claridad: 'c80', 'c50', 'ts', 
    Relacion senal ruido 'snr'
    Directo reverberante 'dr'
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
        print('Generando nuevo banco ')
        if (len(bankname.split('_')) > 1):
            (noct,bwoct) = [int(ss) for ss in bankname.split('_')[-2:]]
            make_filterbank(noct=noct,bwoct=bwoct,bankname=bankname)
        else:
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
    pars = dict.fromkeys(listofkeys,0 )
    pars['nchan'] = nchan
    pars['nbands'] = nbands+2
    pars['fc'] = [None]*pars['nbands']
    pars[method] = np.zeros((pars['nbands'],pars['nchan']))
    pars['edt'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['tfit'] = np.zeros((pars['nbands'],pars['nchan'],2))
    pars['lfit'] = np.zeros((pars['nbands'],pars['nchan'],2))
    pars['schr'] = np.zeros((pars['nbands'],pars['nchan'],nmax))
    pars['rvalue'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['snr'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['c80'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['c50'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['ts'] = np.zeros((pars['nbands'],pars['nchan']))
    pars['dr'] = np.zeros((pars['nbands'],pars['nchan']))
    # Por Bandas de frecuencia primero
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
        pars['edt'][n], *_ = revtime(data_filt,'edt',fs,tmax)
        pars[method][n], pars['tfit'][n], pars['lfit'][n], pars['schr'][n], pars['snr'][n], pars['rvalue'][n] = revtime(data_filt,method,fs,tmax)
        pars['c80'][n], pars['c50'][n], pars['ts'][n] = clarity(data_filt,fs,tmax)
        pars['dr'][n] = direct_to_reverb(data_filt,fs)

    return pars

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

# modificar para que sea multicanal, por ahora hay que pasar data[:,0]
def find_echoes(data, nechoes=10, pw=1.0, fs=48000):
    nw = int(np.floor(0.5*pw*fs/1000))
    amp = 1-np.exp(-np.square(np.linspace(-3.0,3.0,6*nw)))
    echoes = np.empty((nechoes,2))
    data_copy = np.copy(data)
    for n in range(nechoes):
        n0 = np.argmax(np.abs(data_copy))
        echoes[n,0] = n0/fs
        echoes[n,1] = np.sum(np.square(data[n0-nw:n0+nw]))
        data_copy[n0-3*nw:n0+3*nw] *= amp
    return echoes  

#echo sorting and echo density

#def find_modes # encuentra modos hasta una frecuencia

#def binaural # aca va ITD ILD e intensidad binaural IACC

#def sti # inteligilibilidad del habla

#def spatial # fraccion de energia lateral




