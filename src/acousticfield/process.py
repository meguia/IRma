import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.interpolate import interp1d
from scipy.fft import next_fast_len, rfft, irfft, fft, ifft
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
    # rec puede ser un nombre de un archivo o un prefijo
    
    if type(rec) is str:
        fs, data = wavfile.read(rec + '.wav')
    elif type(rec) is np.ndarray:
        data = rec
    else:
        raise TypeError('First argument must be the array given by play_rec or a file name')
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D    
    datainv = np.load(fileinv + '_inv.npz')
    _, nchan = np.shape(data)
    if fs != datainv['fs']:
        raise ValueError('sampling rate of inverse filter does not match file sample rate')    
    if datainv['type'] == 'sweep':  
        ir_stack=ir_sweep(data,datainv,nchan)
    elif datainv['type'] == 'golay':
        ir_stack=ir_golay(data,datainv,nchan)
    else:
        raise ValueError("inv_type must be 'sweep' or 'golay'") 
    # ir dimensions: Nrep, nsamples, nchan
    Nrep,N,_ = ir_stack.shape
    if loopback is not None:
        # usar el loopback para alinear todos los otros canales
        n0 = np.argmax(ir_stack[:,:,loopback],axis=1)
    else:
        n0 = np.zeros((Nrep,),dtype=int)
    if dur is None:
        ndur = np.min(int(N/2)-n0)
    else:
        ndur = int(np.round(dur*fs))
    ir_align = np.zeros((Nrep,ndur,nchan))
    for n in range(nchan):
        for m in range(Nrep):
            ir_align[m,:,n] = ir_stack[m,n0[m]:n0[m]+ndur,n]
    ir = np.mean(ir_align,axis=0)
    ir_std = np.std(ir_align,axis=0)
    if loopback is not None:
        ir = np.delete(ir ,loopback ,1)
        ir_std = np.delete(ir_std ,loopback ,1)  
    wavfile.write(fileout + '.wav',fs,ir)
    np.savez(fileout,ir=ir,ir_std=ir_std,ir_stack=ir_stack,fs=fs,loopback=loopback)
    return ir

def ir_sweep(data,datainv,nchan):
    invsweepfft = datainv['invsweepfft']
    N = invsweepfft.shape[0]
    Nrep = datainv['Nrep']
    invfilt =  invsweepfft[np.newaxis,:,np.newaxis]
    data_stack = np.reshape(data[:N*Nrep,:],(Nrep,N,nchan))
    data_fft=fft(data_stack,N,axis=1)
    ir_stack =  np.real(ifft(data_fft*invfilt,axis=1))
    return ir_stack

def ir_golay(data,datainv,nchan):
    a = datainv['a']
    b = datainv['b']
    Ng = len(a)
    Nrep = datainv['Nrep']
    rc_stack = np.reshape(data[:2*Ng*Nrep],(Nrep,2,Ng,nchan))
    A = rfft(a,Ng,norm="ortho")
    Ap = rfft(rc_stack[:,0,:,:],Ng,axis=1,norm="ortho")
    B = rfft(b,Ng,norm="ortho")
    Bp = rfft(rc_stack[:,1,:,:],Ng,axis=1,norm="ortho")
    aa = irfft(Ap*np.conj(A[np.newaxis,:,np.newaxis]),axis=1,norm="ortho")
    bb = irfft(Bp*np.conj(B[np.newaxis,:,np.newaxis]),axis=1,norm="ortho")
    ir_stack = aa+bb
    return ir_stack

    

def fconvolve(in1,in2):
    '''
    in1 can be multichannel, in2 single channel
    '''
    #the samples must be along axis -1
    n1 = np.max(in1.shape)
    n2 = np.max(in2.shape)
    ntot = n1+n2-1
    if np.argmin(in1.shape)>0:
        in1_fft=rfft(in1.T,ntot)
    else:
        in1_fft=rfft(in1,ntot) 
    if np.argmin(in2.shape)>0:
        in2_fft=rfft(in2.T,ntot)
    else:
        in2_fft=rfft(in2,ntot) 
    return irfft(in1_fft*in2_fft).T


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
    Computes the power spectrum (in dB) of signal data
    Can be used to obtain the transfer function from the impulse response 
    Returns a dictionary sp with keys
    sp['f'] center frequencies
    sp['s'] power spectrum in dB 
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

def crossspectrum(data_input, ch1=0, ch2=1, fs=48000):
    """
    Computes the cross/auto power spectrum between two channels of signal data 
    Data_input must be at least nsamples x 2 and chan1 , chan2 are the channels
    for computing the cross/auto power spectrum
    It can be used to obtain the transfer function between two signals
    Returns a dictionary xsp with keys
    xsp['f'] center frequencies
    xsp['S21'] cross power spectrum sp2 sp1*
    xsp['S11'] auto power spectrum sp1 sp1*
    xsp['S22'] auto power spectrum sp2 sp2*
    xsp['H'] transfer 1 -> 2 sp2/sp1 = S21/S11 
    """
    if type(data_input) is str:
        fs, data = wavfile.read(data_input + '.wav')
    elif type(data_input) is np.ndarray:
        data = data_input
    else:
        raise TypeError('First argument must be an nparray or a filename')    
    if data.ndim == 1:
        raise TypeError('You must provide at least 2 channels')    
    nsamples, nchan = np.shape(data)
    nf = int(np.ceil((nsamples+1)/2))
    freq = fftfreq(nsamples, d=1/fs)
    listofkeys = ['chans','f','S21','S11','S22','H']
    xsp = dict.fromkeys(listofkeys,0 )
    xsp['chans'] = (ch1,ch2)
    xsp['f'] = np.abs(freq[:nf])
    sp1 = rfft(data[:,ch1])
    sp2 = rfft(data[:,ch2])
    xsp['S21'] = sp1*np.conjugate(sp2)
    xsp['S11'] = sp1*np.conjugate(sp1)
    xsp['S22'] = sp2*np.conjugate(sp2)
    # now we take care of the possible divergences
    eps = 1e-12
    xsp['H'] = sp2/(sp1+eps)
    return xsp

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

def lowpass_filter(data, **kwargs):
    nyq = 0.5 * kwargs['fs']
    hicut = kwargs['hicut'] / nyq
    sos = signal.butter(kwargs['order'], hicut, btype='lowpass', output='sos')
    return signal.sosfiltfilt(sos, data, axis=0)    


# agregar una funcion para detectar clipeo
        





    
    
    
    
