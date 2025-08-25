import numpy as np
from scipy import signal
from scipy.fft import next_fast_len,fft,ifft,rfft,irfft
from scipy.io import wavfile
from .process import fadeinout, burst


def sweep(T, f1=30, f2=22000,filename=None,fs=48000,Nrep=1,order=2,post=2.0,rms=-3.2):
    '''
    Generates an exponential sweep signal of duration T with a sampling frequency fs 
    starting from frequency f1 to f2, stores it in filename.wav and saves the inverse filter in filename_inv.npy
    optional parameters can modify the fadein and fadeout of the signal with fade
    uses the method of Muller and Massarani, "Transfer Function Measurement with Sweeps" 
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
    sweep = np.real(ifft(cplx)) # Y aca esta el sweep finalmente
    sweep = sweep/max(np.abs(sweep)) # normaliza
    
    if post is not None: # zeropadding for better accuracy
        npost = int(fs*post)
        NL = next_fast_len(N+npost)
    else:    
        NL = next_fast_len(N)
    if NL>len(sweep):
        print("PAD")
        np.pad(sweep,(0,NL-len(sweep)))    
    else:
        sweep = sweep[:NL]
    rms_sweep = 10.0*np.log10(np.mean(np.square(sweep[:NL-npost]))) # deberia ser -3 dB
    rms_diff = rms - rms_sweep
    if (rms_diff<0):
        sweep = sweep*np.power(10.0,rms_diff/20.0) # ajusta la rams
    else:
        print('Warning RMS pedido mayor al RMS de corte que es {0:.2f} dB '.format(rms_sweep))  
    rms_sweep = 10*np.log10(np.mean(np.square(sweep[:NL-npost])))
    print('Sweep RMS = {0:.2f} dB '.format(rms_sweep))    
    w = signal.windows.hann(2*Gd_start) # ventana para fadein
    sweep[:Gd_start] = sweep[:Gd_start]*w[:Gd_start]
    w = signal.windows.hann(2*postfade) # ventana para fadeout
    sweep[-postfade:] = sweep[-postfade:]*w[-postfade:]
    # Calculo del filtro inverso normalizado
    sweepfft = fft(sweep)
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

# Multitone

#Golay complementary sequences
def golay(filename,N=18,fs=48000, Nrep=1):
    """
    Generate Golay complementary sequences.
    """
    a = np.array([1.0,1.0])
    b = np.array([1.0,-1.0])
    for n in range(N):
        new_a = np.hstack((a,b))
        b = np.hstack((a,-b))
        a = new_a
    ab = np.tile(np.hstack((a,b)),Nrep)
    Ng = len(a)
    A = rfft(a,Ng,norm="ortho")
    B = rfft(b,Ng,norm="ortho")
    normA =  np.max(np.abs(irfft(A*np.conj(A),norm="ortho")))
    normB =  np.max(np.abs(irfft(B*np.conj(B),norm="ortho")))
    print('Golay complementary sequence generated with {0} samples each.'.format(len(a)))
    print('Total signal with {0} repetitions has a duration of {1:.2f} seconds'.format(Nrep,len(ab)/fs))
    np.savez(filename + '_inv',a=a/normA,b=b/normB,type='golay',fs=fs,Nrep=Nrep)
    wavfile.write(filename + '.wav',fs,ab*0.999) 
    return ab


def sigmoid(x,x0,s=1.0):
    """
    Compute the sigmoid function.
    The input x is the value (or array) to be transformed, x0 is the midpoint, and s is the slope.
    """
    x1 = 2*(x-x0)/s
    sig = np.zeros_like(x1)
    ncut = np.argmax(x1>0)
    sig[:ncut] = np.exp(x1[:ncut])/(1.0 + np.exp(x1[:ncut]))
    sig[ncut:] = 1.0/(1.0 + np.exp(-x1[ncut:]))
    return sig    

def puretone(T,f,fadein=None,fadeout=None,fs=48000):
    """
    Generate a pure tone signal of frequency f.
    """
    data = np.sin(2.0*np.pi*f*np.arange(0,T,1/fs))
    fadeinout(data, fadein=fadein, fadeout=fadeout, fs=fs)
    return data

def whitenoise(T, flow=None, fhigh=None, fslow=None, fshigh=None, nchannels=1, fadein=None, fadeout=None, fs=48000, filename="wnoise"):
    """
    Generate white noise of duration T limited to the band between flow and fhigh (fslow and fshigh give the slopes of
    the sigmoid function for the band limits) can generate nchannels channels
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
    wavfile.write(filename + '.wav',fs,wnoise) 
    return wnoise

def pinknoise(T, ncols=16, fadein=None, fadeout=None, fs=48000):
    """
    Generate pink noise of duration T using the Voss-McCartney algorithm.
    ncols: number of independent sources
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

