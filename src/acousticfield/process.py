import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.interpolate import interp1d
from scipy.fft import next_fast_len, rfft
from numpy.fft.helper import fftfreq


def ir_extract(rec,fileinv,fileout='ir_out',loopback=None,dur=None,fs=48000):
    '''
    extrae la respuesta impulso a partir de la grabacion del sweep (rec) y el filtro inverso 
    almacenado en fileinv (archivo npy), ambos parametros obligatorios.
    rec puede ser el array numpy de nsamp x nchan o el nombre del archivo wav. 
    Si hay un canal de loopback lo usa para alinear y hay que proporcionar el numero de canal
    devuelve la ri obtenida (puede ser mas de un canal) y la almacena en fileout 
    (si la entrada fue un archivo) con una duracion dur (la ir completa por defecto)
    '''
    #modificar para admitir rec de tres dimensiones
    # rec puede ser un nombre de un archivo o un prefijo
    
    if type(rec) is str:
        fs, sweep = wavfile.read(rec + '.wav')
        if sweep.ndim == 1:
            sweep = sweep[:,np.newaxis] # el array debe ser 2D
    elif type(rec) is np.ndarray:
        sweep = rec
    else:
        raise TypeError('Primer argumento debe ser el array devuelto por play_rec o un nombre de archivo')
    invsweepfft = np.load(fileinv + '_inv.npy')
    nchan = sweep.shape[1]
    nsamp = invsweepfft.shape[0]
    ir = np.zeros((nsamp,nchan))
    for n,chan in enumerate(sweep.T):
        ir[:,n] = irsweep(chan,invsweepfft)
    if loopback is not None:
        # usar el loopback para alinear todos los otros canales
        n0 = np.argmax(ir[:,loopback])
        ir = ir[n0:]
        ir = np.delete(ir ,loopback ,1)
    if type(rec) is str:    
        # aca hacer que renombre siguiendo el nombre del archivo de entrada
        wavfile.write(fileout + '.wav',fs,ir)
        if dur is not None:
            ndur = int(np.round(dur*fs))
            ir = ir[:ndur,:]
    return ir

# renombrar o llamar a scipy.signal.fftconvolve
# funcion para convolucion en el dominio del tiempo y en el dominoo de frecuencia
def irsweep(sweep,invsweepfft):
    '''
    Aplica el filtro inverso invsweepfft al array sweep de una dimension
    '''
    sweepfft=np.fft.fft(sweep,len(invsweepfft))
    ir = np.real(np.fft.ifft(invsweepfft*sweepfft))
    return ir

# funcion para hacer time stretch y compensar variaciones de temperatura o corregir drift en el clock
#def ir_stretch(ir,threshold):

# funcion para detectar outliers en un conjunto de IR
#def ir_average(ir,reject_outliers=True,threshold): # con opcion de eliminar outliers
# fadeinout

def fadeinout(data, fadein=0.05, fadeout=None, fs=48000):
    if fadein is not None:
        nin = int(fadein*fs)
        a = (1.0-np.cos(np.linspace(0,np.pi,nin)))/2.0 
        if data.ndim == 2:
            for n in range(data.shape[1]):
                data[:nin,n]  *= a
        else:
            data[:nin] *= a
    if fadeout is not None:
        nout = int(fadeout*fs)
        a = (1.0+np.cos(np.linspace(0,np.pi,nout)))/2.0 
        if data.ndim == 2:
            for n in range(data.shape[1]):
                data[-nout:,n]  *= a
        else:
            data[-nout:] *= a        
    return
    
def burst(data, nburst=3, dur=0.05, gap=0.02, fadein=0.01, fadeout=None, fs=48000):
    a = np.zeros((len(data),))
    dn = int(np.floor(dur*fs))
    for n in range(nburst):
        n1 = int(np.floor(n*(dur+gap)*fs))
        n2 = n1 + dn
        a[n1:n2] = 1.0
        if fadein is not None:
            nin = int(fadein*fs)
            a[n1:n1+nin] = (1.0-np.cos(np.linspace(0,np.pi,nin)))/2.0 
        if fadeout is not None:
            nout = int(fadeout*fs)
            a[n2-nout:n2] = (1.0+np.cos(np.linspace(0,np.pi,nout)))/2.0 
    if data.ndim == 2:
        for n in range(data.shape[1]):
            data[:,n]  *= a
    else:
        data *= a        
    return

#filtros

def butter_bandpass(lowcut, highcut, fs, order=5, N=10000):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    sos = signal.butter(order, [low, high], btype='band', output='sos')
    w, h = signal.sosfreqz(sos,worN=N)
    return sos, w, h

def make_filterbank(fmin=62.5,noct=8,bwoct=1,fs=48000,order=5,N=10000,bankname='fbank_8_1',show=False):
    '''
    Arma un banco de filtros de noct octavas desde la frecuencia fmin con bwoct filtros
    por octava con filtros butter de orden order en formato sos y los guarda en bankname
    '''
    nfilt = (noct-1)*bwoct+1 # las octavas inicial y final inclusive
    fc = np.array([fmin* 2 ** (n * 1 / bwoct) for n in range(nfilt)])
    lf = 2. ** (-0.5/bwoct)*fc
    sos = np.zeros((nfilt,order,6),dtype=np.float64)
    for n, f0 in enumerate(lf):
        sos[n], w, h = butter_bandpass(f0,f0*2**(1/bwoct),fs,order,N)
        #if show:
        #    plt.semilogx((fs * 0.5 / np.pi) * w, abs(h))
    np.savez_compressed(bankname,sos=sos,fc=fc,fs=fs,order=order)
    print('Banco de filtros generado: ' + str(noct) + ' octavas,' + str(bwoct) + ' bandas/octava,' +
          'desde ' + str(fmin) + ' Hz,' + 'Almacenada en archivo ' + bankname)
    #if show:
    #    plt.show()
    return
    
def A_weighting(fs=48000):
    """
    Diseña filtro A para la frecuencia de sampleo fs
    adaptado de https://gist.github.com/endolith/148112
    Usage: B, A = A_weighting(fs) 
    """
    z = [0, 0, 0, 0]
    p = [-2*np.pi*20.598997057568145,
         -2*np.pi*20.598997057568145,
         -2*np.pi*12194.21714799801,
         -2*np.pi*12194.21714799801,
         -2*np.pi*107.65264864304628,
         -2*np.pi*737.8622307362899]
    k = 1
    # Normalize to 0 dB at 1 kHz for all curves
    b, a = signal.zpk2tf(z, p, k)
    k /= abs(signal.freqs(b, a, [2*np.pi*1000])[1][0])
    z_d, p_d, k_d = signal.bilinear_zpk(z, p, k, fs)
    return signal.zpk2sos(z_d, p_d, k_d)
   


def apply_bands(data, bankname='fbank_10_1', fs=48000, norma=True):
    """
    Aplica el banco de filtros almacenado en bankname a la senal data
    por defecto normaliza las senales filtradas, sino hacer norma=false
    """
    try:     
        fbank = np.load(bankname + '.npz')
    except:
        make_filterbank(bankname=bankname)
        fbank = np.load(bankname + '.npz')
    data = data - np.mean(data)
    nsamples = len(data)
    nbands, order, dd = fbank['sos'].shape
    data_filt = np.empty((nsamples,nbands))
    for n in range(nbands):
        temp = signal.sosfiltfilt(fbank['sos'][n], data)
        if (norma):
            temp = temp/np.amax(np.abs(temp))
        data_filt[:,n] = temp
    # agregar fadeinfadeout    
    return data_filt    

def spectrum(data_input, fs=48000):
    """
    Computes the spectral power density (in dB) of signal data
    Can be usede to obtain the transfer functio from the impulse response 
    Rturns a dictionary sp with keys
    sp['f'] center frequencies
    sp['s'] power spectral density in dB 
    sp['amplitude'] amplitude of the FFT
    sp['phase] phase of the FFT for signal reconstruction
    """
    if type(data_input) is str:
        fs, data = wavfile.read(data_input + '.wav')
    elif type(data_input) is np.ndarray:
        data = data_input
    else:
        raise TypeError('Primer argumento debe ser el array devuelto por extractir o un nombre de archivo')
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nf = int(np.ceil((nsamples+1)/2))
    freq = fftfreq(nsamples, d=1/fs)
    listofkeys = ['nchan','f','s','amplitude','phase']
    sp = dict.fromkeys(listofkeys,0 )
    sp['nchan'] = nchan
    sp['f'] = np.abs(freq[:nf])
    sp['s'] = np.zeros((nchan,nf))
    sp['amplitude'] = np.zeros((nchan,nf))
    sp['phase'] = np.zeros((nchan,nf))
    for n in np.arange(nchan):
        s = rfft(data[:,n])
        sp['amplitude'][n] = np.abs(s)
        sp['phase'][n] = np.angle(s)
        sp['s'][n] = 20*np.log10(sp['amplitude'][n])
    return sp


def spectrogram(data, **kwargs):
    """
    Computes the spectrogram and the analytic envelope of the signal
    """
    #force to power of next fast FFT length
    windowSize = next_fast_len(kwargs['windowSize'])
    overlap = kwargs['overlap']
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nt = int(np.floor((nsamples-windowSize)/(windowSize-overlap)))+1
    nenv = next_fast_len(nsamples)
    # Dict for spectrogram
    listofkeys = ['nchan','nsamples','f','t','s','env','nt','nf','df','window','overlap']
    spec = dict.fromkeys(listofkeys,0 )
    spec['nchan'] = nchan
    spec['nf'] = windowSize//2+1
    spec['s'] = np.zeros((nchan,spec['nf'],nt))
    spec['env'] = np.zeros((nchan,nenv))
    spec['window'] = windowSize
    spec['overlap'] = overlap
    spec['nt'] = nt
    spec['nsamples']=nsamples
    for n in np.arange(nchan):
        env = np.abs(signal.hilbert(data[:,n],nenv))  
        f,t,spectro = signal.spectrogram(data[:,n], kwargs['fs'], window=kwargs['windowType'], nperseg=windowSize, noverlap=overlap)
        spec['t'] = t
        spec['df'] = f[1]
        spec['env'][n] = env
        if kwargs['logf']:
            lf = np.power(2,np.linspace(np.log2(f[1]),np.log2(f[-1]),spec['nf']))
            fint = interp1d(f,spectro.T,fill_value="extrapolate")
            spec['f'] = lf
            spec['s'][n] = fint(lf).T
        else:
            spec['f'] = f
            spec['s'][n] = spectro
        if kwargs['normalized']:
            spec['s'][n] = spec['s'][n]/np.max(spec['s'][n])
            spec['env'][n] = spec['env'][n]/np.max(spec['env'][n])    
    return spec        

def hipass_filter(data, **kwargs):
    nyq = 0.5 * kwargs['fs']
    low = kwargs['lowcut'] / nyq
    sos = signal.butter(kwargs['order'], low, btype='highpass', output='sos')
    return signal.sosfiltfilt(sos, data, axis=0)



        





    
    
    
    
