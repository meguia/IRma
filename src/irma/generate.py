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
    Gd_start = int(np.ceil(min(N/10,max(fs/f1, N/200)))) # group delay start fs/f1 bounded between N/10 and N/200
    postfade = int(np.ceil(min(N/10,max(fs/f2,N/200)))) # fade-out length
    Nsweep = N - Gd_start - postfade
    tsweep = Nsweep/fs
    # bandpass filters to create the desired frequency response
    if (f2 < fs/2):
        B2, A2 = signal.butter(order,f2/(fs/2)) # lowpass
        B1, A1 = signal.butter(order,f1/(fs/2),'highpass') # higpass
    else:
        B2 = [1,2,1]
        A2 = B2
        B1, A1 = signal.butter(2,f1/(fs/2),'highpass' ) # order 2
    W1, H1 = signal.freqz(B1,A1,N+1,fs=fs)
    W2, H2 = signal.freqz(B2,A2,N+1,fs=fs)   
    # pink spectrum (-10 dB per decade, or 1/sqrt(f))
    mag = np.sqrt(f1/W1[1:])
    mag = np.insert(mag,0,mag[0]) # fill f=0
    mag = mag*np.abs(H1)*np.abs(H2) # apply bandpass
    Gd = tsweep * np.cumsum(mag**2)/np.sum(mag**2) # compute group delay
    Gd = Gd + Gd_start/fs # add pre-delay
    Gd = Gd*fs/2   # convert to samples
    ph = -2.0*np.pi*np.cumsum(Gd)/(N+1) # obtain phase by integrating GD
    ph = ph - (W1/(fs/2))*np.mod(ph[-1],2.0*np.pi) # force phase to end at multiple of 2π
    cplx = mag*np.exp(1.0j*ph) # build sweep spectrum from magnitude and phase
    cplx = np.append(cplx,np.conj(cplx[-2:0:-1])) # complete spectrum with negative freqs for real sweep
    sweep = np.real(ifft(cplx)) # final sweep
    sweep = sweep/max(np.abs(sweep)) # normalize
    
    if post is not None: # zeropadding for better accuracy
        npost = int(fs*post)
    else:
        npost = 0    
    NL = next_fast_len(N+npost)
    if NL>len(sweep):
        print("PAD")
        sweep = np.pad(sweep,(0,NL-len(sweep)))    
    else:
        sweep = sweep[:NL]
    rms_sweep = 10.0*np.log10(np.mean(np.square(sweep[:NL-npost]))) # should be about -3 dB
    rms_diff = rms - rms_sweep
    if (rms_diff<0):
        sweep = sweep*np.power(10.0,rms_diff/20.0) # adjust RMS
    else:
        print('Warning: requested RMS exceeds cutoff RMS of {0:.2f} dB'.format(rms_sweep))  
    rms_sweep = 10*np.log10(np.mean(np.square(sweep[:NL-npost])))
    print('Sweep RMS = {0:.2f} dB '.format(rms_sweep))    
    w = signal.windows.hann(2*Gd_start) # window for fade-in
    sweep[:Gd_start] = sweep[:Gd_start]*w[:Gd_start]
    w = signal.windows.hann(2*postfade) # window for fade-out
    sweep[-postfade:] = sweep[-postfade:]*w[-postfade:]
    # Compute normalized inverse filter
    sweepfft = fft(sweep)
    invsweepfft = 1.0/sweepfft
    # re-apply bandpass to avoid divergences
    W1, H1 = signal.freqz(B1,A1,NL,whole=True,fs=fs)
    W2, H2 = signal.freqz(B2,A2,NL,whole=True,fs=fs)
    invsweepfftmag  = np.abs(invsweepfft)*np.abs(H1)*np.abs(H2)
    invsweepfftphase = np.angle(invsweepfft)
    invsweepfft = invsweepfftmag*np.exp(1.0j*invsweepfftphase) # resynthesis
    print('Sweep generated with {0} samples.'.format(len(sweep)))
    print('Total signal with {0} repetitions has a duration of {1:.2f} seconds'.format(Nrep,Nrep*len(sweep)/fs))
    np.savez(filename + '_inv',invsweepfft=invsweepfft,type='sweep',fs=fs,Nrep=Nrep) 
    wavfile.write(filename + '.wav',fs,np.tile(sweep,Nrep)) # saves the sweep to WAV in 32-bit float format
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

