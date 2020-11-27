import numpy as np
import sounddevice as sd
import pandas as pd
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from scipy.interpolate import interp1d
from matplotlib import pyplot as plt
from IPython.display import display, HTML

def load_pcm(file,nchan,nbytes=4):
    """
    Function to load a raw PCM audio file with nchan channels and nbytes little endian
    """
    nmax = 2**(nbytes*8-1)
    data=np.memmap(file, dtype='u1', mode='r')
    nsamples=data.shape[0]//(nchan*nbytes)
    if nbytes==4:
        realdata=np.reshape(data.view(np.int32)/nmax,(nsamples,nchan)).astype('float64')
    elif nbytes==2:
        realdata=np.reshape(data.view(np.int16)/nmax,(nsamples,nchan)).astype('float32')
    elif nbytes==1:
        realdata=np.reshape(data.view(np.int8)/nmax,(nsamples,nchan)).astype('float32')
    else:
        raise Exception("Only 4,2 or 1 bytes allowed")
    return realdata




def time_rec(filerec,duration,delay=0,chanin=[0],fs=48000,sdevice=None,write_wav=True):
    '''
    funcion grabar durante dur segundos en una cantidad arbitraria de canales de entrada dada por chanin (lista)
    en archivo filerec. 
    '''
    #agregar una alerta de clipeo y la opcion de correr dummy
    if sdevice is not None:
        sd.default.device = sdevice
    sd.default.samplerate = fs
    nchanin = chanin[-1]+1
    # loop sobre repeat
    rec = sd.rec(int(duration*fs),samplerate=fs,channels=nchanin,dtype='float64') # graba con 64 bits para proceso
    sd.wait() # espera que termine la grabacion
    print('listo')
    rec = rec[:,chanin]
    if write_wav:
        wavfile.write(filerec + '.wav',fs,rec) # guarda el array grabado en wav con 32 bits
    # fin loop   
    return rec

def play_rec(fileplay,filerec,delay=0,repeat=1,chanout=[0],chanin=[0],revtime=2.0,sdevice=None,write_wav=True):
    '''
    funcion para reproducir el archivo mono wav fileplay a traves de los canales de salida chanout (lista)
    y grabarlo simultaneamente en una cantidad arbitraria de canales de entrada dada por chanin (lista)
    en archivo filerec. Puede cambiarse la cantidad de segundos que graba luego de que se extinguio 
    la senal revtime y cambiar el device si no se usa el default 
    '''
    #agregar una alerta de clipeo y la opcion de correr dummy
    if sdevice is not None:
        sd.default.device = sdevice
    fs, data = wavfile.read(fileplay + '.wav')    
    sd.default.samplerate = fs
    nchanin = chanin[-1]+1
    nchanout = chanout[-1]+1
    data = np.append(data,np.zeros(int(revtime*fs))) # extiende data para agregar la reverberacion
    data = np.repeat(data[:,np.newaxis],nchanout,1) # repite el array 
    # wait delay e imprimir algun algun mensaje
    # loop sobre repeat
    rec = sd.playrec(data, channels=nchanin,dtype='float64') # graba con 64 bits para proceso
    sd.wait() # espera que termine la grabacion
    print('listo')
    rec = rec[:,chanin]
    if write_wav:
        wavfile.write(filerec + '.wav',fs,rec) # guarda el array grabado en wav con 32 bits
    # fin loop   
    return rec

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

# funcion para hacer time stretch y compensar variaciones de temperatura
#def ir_stretch(ir,threshold):

# funcion para detectar outliers en un conjunto de IR
#def ir_average(ir,reject_outliers=True,threshold): # con opcion de eliminar outliers


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
        if show:
            plt.semilogx((fs * 0.5 / np.pi) * w, abs(h))
    np.savez_compressed(bankname,sos=sos,fc=fc,fs=fs,order=order)
    print('Banco de filtros generado: ' + str(noct) + ' octavas,' + str(bwoct) + ' bandas/octava,' +
          'desde ' + str(fmin) + ' Hz,' + 'Almacenada en archivo ' + bankname)
    if show:
        plt.show()
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
# Spectrogram

def spectrogram(data, windowSize=512, overlap=None, fs=48000, windowType='hanning', normalized=False, logf=False):
    """
    Computa el espetrograma de la senal data
    devuelve spec un diccionario con keys 
    """
    #force to power of two
    windowSize = np.power(2,int(np.around(np.log2(windowSize))))
    if overlap is None:
        overlap = windowSize//8
    if type(data) is str:
        fs, data = wavfile.read(data + '.wav')
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nt = int(np.ceil((nsamples-windowSize)/(windowSize-overlap)))
    # Dict for spectrogram
    listofkeys = ['nchan','f','t','s','nt','nf','df','window','type','overlap','log']
    spec = dict.fromkeys(listofkeys,0 )
    spec['nchan'] = nchan
    spec['nf'] = windowSize//2+1
    spec['s'] = np.zeros((nchan,spec['nf'],nt))
    spec['window'] = windowSize
    spec['type'] = windowType
    spec['overlap'] = overlap
    spec['logf'] = logf
    spec['nt'] = nt
    for n in np.arange(nchan):       
        f,t,spectro = signal.spectrogram(data[:,n], fs, window=windowType, nperseg=windowSize, noverlap=overlap)
        spec['t'] = t
        spec['df'] = f[1]
        print(spectro.shape)
        if logf:
            lf = np.power(2,np.linspace(np.log2(f[1]),np.log2(f[-1]),spec['nf']))
            fint = interp1d(f,spectro.T,fill_value="extrapolate")
            spec['f'] = lf
            spec['s'][n] = fint(lf).T
        else:
            spec['f'] = f
            spec['s'][n] = spectro
    if normalized:
        spec['s'] = spec['s']/np.max(spec['s'])    
    return spec    
        





    
    
    
    
