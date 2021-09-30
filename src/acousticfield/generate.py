import numpy as np
from scipy import signal
from scipy.fft import next_fast_len
from scipy.io import wavfile
from .process import fadeinout, burst


def sweep(T, f1=30, f2=22000,filename=None,fs=48000,Nrep=1,order=2,post=2.0):
    '''
    Genera un sweep exponencial de duracion T con frecuencia de sampleo fs desde la frecuencia f1
    hasta f2, lo almacena en filename.wav y guarda el filtro inverso en filename_inv.npy
    como parametros opcionales se pueden modificar el fadein y fadeout de la senal con fade
    usa el metodo de Muller and Massarani, "Transfer Function Measurement with Sweeps" 
    que era el implementado en Matlab. El unico cambio es que puede elegirse el orden del filtro
    '''
    if filename is None:
        filename = 'sweep' + str(T) + 's_' + str(f1) + '_' + str(f2)   
    N = int(T*fs)
    Gd_start = int(np.ceil(min(N/10,max(fs/f1, N/200)))) # inicio del group delay fs/f1 acotado entre N/10 y N/200
    postfade = int(np.ceil(min(N/10,max(fs/f2,N/200)))) # fadeout 
    Nsweep = N - Gd_start - postfade
    tsweep = Nsweep/fs
    # filtros pasabanda para crear la respuesta en frecuencia deseada
    if (f2 < fs/2):
        B2, A2 = signal.butter(order,f2/(fs/2)) # lowpass
        B1, A1 = signal.butter(order,f1/(fs/2),'highpass') # higpass
    else:
        B2 = [1,2,1]
        A2 = B2
        B1, A1 = signal.butter(2,f1/(fs/2),'highpass' ) # order 2
    W1, H1 = signal.freqz(B1,A1,N+1,fs=fs)
    W2, H2 = signal.freqz(B2,A2,N+1,fs=fs)   
    # espectro rosa (-10dB por decada, or 1/(sqrt(f)) 
    mag = np.sqrt(f1/W1[1:])
    mag = np.insert(mag,0,mag[0]) # completamos f=0
    mag = mag*np.abs(H1)*np.abs(H2) # y aplicamos pasabanda\
    Gd = tsweep * np.cumsum(mag**2)/np.sum(mag**2) # calculo del group delay
    Gd = Gd + Gd_start/fs # agrega el predelay
    Gd = Gd*fs/2;   # convierte a samples
    ph = -2.0*np.pi*np.cumsum(Gd)/(N+1) # obtiene la fase integrando el GD
    ph = ph - (W1/(fs/2))*np.mod(ph[-1],2.0*np.pi) # fuerza la fase a terminar en multiplo de 2 pi
    cplx = mag*np.exp(1.0j*ph) # arma el espectro del sweep a partir de la magnitud y la fase
    cplx = np.append(cplx,np.conj(cplx[-2:0:-1])) # completa el espectro con f negativas para sweep real
    sweep = np.real(np.fft.ifft(cplx)) # Y aca esta el sweep finalmente
    if post is not None: # zeropadding for better accuracy
        npost = int(fs*post)
        NL = next_fast_len(N+npost)
    else:    
        NL = next_fast_len(N)
    if NL>len(sweep):
        np.pad(sweep,(0,NL-len(sweep)))    
    else:
        sweep = sweep[:NL]    
    w = signal.hann(2*Gd_start) # ventana para fadein
    sweep[:Gd_start] = sweep[:Gd_start]*w[:Gd_start]
    w = signal.hann(2*postfade) # ventana para fadeout
    sweep[-postfade:] = sweep[-postfade:]*w[-postfade:]
    sweep = sweep/max(np.abs(sweep)) # normaliza
    # Calculo del filtro inverso
    sweepfft = np.fft.fft(sweep)
    invsweepfft = 1.0/sweepfft
    #  para evitar divergencias re aplicamos el pasabanda
    W1, H1 = signal.freqz(B1,A1,NL,whole=True,fs=fs)
    W2, H2 = signal.freqz(B2,A2,NL,whole=True,fs=fs)
    invsweepfftmag  = np.abs(invsweepfft)*np.abs(H1)*np.abs(H2)
    invsweepfftphase = np.angle(invsweepfft)
    invsweepfft = invsweepfftmag*np.exp(1.0j*invsweepfftphase) # resintesis
    print('Sweep generated with {0} samples.'.format(len(sweep)))
    print('Total signal with {0} repetitions has a duration of {1:.2f} seconds'.format(Nrep,Nrep*len(sweep)/fs))
    np.savez(filename + '_inv',invsweepfft=invsweepfft,type='sweep',fs=fs,Nrep=Nrep) 
    wavfile.write(filename + '.wav',fs,np.tile(sweep,Nrep)) # guarda el sweep en wav con formato float 32 bits
    return sweep

# MLS Sequence

#Golay complementary sequences
def golay(filename,N=18,fs=48000, Nrep=1):
    a = np.array([1,1])
    b = np.array([1,-1])
    for n in range(N):
        new_a = np.hstack((a,b))
        b = np.hstack((a,-b))
        a = new_a
    ab = np.tile(np.hstack((a,b)),Nrep)
    print('Golay complementary sequence generated with {0} samples each.'.format(len(a)))
    print('Total signal with {0} repetitions has a duration of {1:.2f} seconds'.format(Nrep,len(ab)/fs))
    np.savez(filename + '_inv',a=a,b=b,type='golay',fs=fs,Nrep=Nrep)
    wavfile.write(filename + '.wav',fs,ab*0.999) 
    return ab


def sigmoid(x,x0=0,a=1):
    x1 = 2*(x-x0)/a
    sig = np.where(x1 < 0, np.exp(x1)/(1 + np.exp(x1)), 1/(1 + np.exp(-x1)))
    return sig

def puretone(T,f,fadein=None,fadeout=None,fs=48000):
    data = np.sin(2.0*np.pi*f*np.arange(0,T,1/fs))
    fadeinout(data, fadein=fadein, fadeout=fadeout, fs=fs)
    return data

def whitenoise(T, flow=None, fhigh=None, fslow=None, fshigh=None, nchannels=1, fadein=None, fadeout=None, fs=48000):
    """
    Genera ruido blanco de duracion T limitado en banda entre flow y fhigh (fslow y fshigh dan las pendientes de
    la sigmoidea del limite de banda) puede generar nchannels canales
    """
    nsamples = int(fs*T)
    freqs = np.fft.rfftfreq(nsamples, 1/fs)
    freqs[0] = 1/nsamples
    fmax = freqs[-1]
    if flow is not None:
        if fslow is None:
            fslow=flow
        s1 = sigmoid(freqs/fmax,flow/fmax,fslow/fmax)
    else:
        s1 = 1
    if fhigh is not None:
        if fshigh is None:
            fshigh=fhigh/4.0
        s2 = sigmoid(freqs/fmax,fhigh/fmax,-fshigh/fmax)
    else:
        s2 = 1
    real = s1*s2*np.random.randn(nchannels, freqs.shape[0])
    imag = s1*s2*np.random.randn(nchannels, freqs.shape[0])
    if not nsamples & 1:
        imag[-1] = 0.
    wnoise = np.array(np.fft.irfft(real + 1j*imag),ndmin=2, dtype='float64').T
    wnoise /= np.abs(wnoise).max(axis=0)
    fadeinout(wnoise, fadein=fadein, fadeout=fadeout, fs=fs)
    return wnoise

def pinknoise(T, ncols=16, fadein=None, fadeout=None, fs=48000):
    """
    Genera ruido rosa de duracion T usando el algoritmo de Voss-McCartney
    ncols: numero de fuente indeptes
    """
    nsamples = int(T*fs)
    array = np.full((nsamples, ncols), np.nan)
    array[0, :] = np.random.random(ncols)
    array[:, 0] = np.random.random(nsamples)
    cols = np.random.geometric(0.5, nsamples)
    cols[cols >= ncols] = 0
    rows = np.random.randint(nsamples, size=nsamples)
    array[rows, cols] = np.random.random(nsamples)
    mask = np.isnan(array)
    idx = np.where(~mask,np.arange(mask.shape[0])[:,None],0)
    array = np.take_along_axis(array,np.maximum.accumulate(idx,axis=0),axis=0)
    pnoise = np.sum(array,axis=1)
    pnoise -= np.mean(pnoise)
    pnoise /= np.abs(pnoise).max(axis=0) 
    fadeinout(pnoise, fadein=fadein, fadeout=fadeout, fs=fs)  
    return pnoise

def burst_noise(nburst, dur, gap, type='white', flow=None, fhigh=None, fslow=None, fshigh=None, nchannels=1, fadein=None, fadeout=None, fs=48000):
    T = nburst*(dur+gap)
    if type == 'white':
        data = whitenoise(T, flow=flow, fhigh=fhigh, fslow=fslow, fshigh=fshigh, nchannels=nchannels, fs=fs)
    elif type == 'pink':
        data = pinknoise(T)
    else:
        raise Exception("Invalid noise type")
    burst(data, nburst=nburst, dur=dur, gap=gap, fadein=fadein, fadeout=fadeout, fs=fs)
    return data
    