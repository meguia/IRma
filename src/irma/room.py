import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress, kurtosis
from .process import make_filterbank, A_weighting, find_dir
from .generate import sigmoid

eps = np.finfo(float).eps

def clamp(i, lo, hi):
    return max(lo, min(i, hi))

def revtime(ir_input, method='RT20', fs=48000, tmax=3.0):
    '''
    Calculates the reverberation time and the Schroeder integral from the impulse response
    stored in ir_input (numpy array or wav file name) using the method 'RT30' 'RT20' or 'EDT'
    It does this for each channel of the fileir.
    Attention assumes by default a maximum decay of 3 seconds (not TR, decay to noise floor
    which is a reasonable assumption in most cases)
    Returns in order:
    - the (the) reverberation times in seconds
    - initial and final time in which the decay line was adjusted
    - initial and final level in dB of the decay line (useful for the rmax method not yet implemented)
    - integral(s) of Schroeder of the entire impulse response
    '''
    if type(ir_input) is str:
        fs, data = wavfile.read(ir_input + '.wav')
    elif type(ir_input) is np.ndarray:
        data = ir_input
    else:
        raise TypeError('First argument must be the array returned by extractir or a file name')
    if data.ndim == 1:
        data = data[:,np.newaxis] # array must be 2D
    nsamples, nchan = np.shape(data)
    nmax = int(min(tmax*fs,nsamples))
    schr = np.zeros((nchan,nmax))
    SNR = np.zeros((nchan,))
    rt = np.zeros((nchan,))*np.nan
    t12 = np.zeros((nchan,2))
    l12 = np.zeros((nchan,2))
    rvalue = np.zeros((nchan,))*np.nan
    for n, ir in enumerate(data.T):
        ns = np.mean(ir[nmax:-1]**2)
        stemp = np.flip(np.cumsum(ir[::-1]**2)) # Schroeder integral
        stemp = stemp[:nmax]
        mm = np.arange(nsamples,0,-1)*ns
        n_ns = np.argmax(stemp<mm[:nmax]*np.sqrt(2))
        xv = 10*np.log10(stemp)-10*np.log10(mm[:nmax])
        xv = xv - np.amax(xv)
        tv =  np.arange(nsamples)/fs # time array
        SNR[n] = -xv[-1] # full decay range SNR
        schr[n][:nmax] = xv
        if method == 'RT30' and SNR[n]>35:
            # Calculate RT using RT30 definition
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-35)
        elif method == 'RT20' and SNR[n]>25:
            # Same as RT20 definition
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-25)
        elif method == 'RT15' and SNR[n]>20:
            # Same as RT20 definition
            pt1 = np.argmax(xv<-5)
            pt2 = np.argmax(xv<-20)
        elif method == 'EDT' and SNR[n]>10.5:
            # Calculate early decay time (EDT)
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
    Calculates clarity values C80 C50 and temporal center TS from the impulse response ir
    later it should take into account the signal-to-noise ratio to avoid overestimating reverberation
    '''
    if type(ir_input) is str:
        fs, data = wavfile.read(ir_input + '.wav')
    elif type(ir_input) is np.ndarray:
        data = ir_input
    else:
        raise TypeError('First argument must be the array returned by extractir or a file name')
    if data.ndim == 1:
        data = data[:,np.newaxis] # array must be 2D
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
    Calculates the following acoustic parameters BY BANDS with the corresponding key names
    Reverberation: 'RT30' (or the requested method), 'EDT'
    Clarity: 'C80', 'C50', 'TS',
    Signal-to-noise ratio 'SNR'
    Direct reverberant 'DRR'
    from the impulse response stored in ir (numpy array or wav file name)
    It does this for each channel of the fileir and for the filter bank stored in bankname (npz extension)
    returns a dictionary rev that has the following keys: nchan (num channels), nbands (num bands), fc (frequencies)
    tr20 (or tr30 or EDT, array of nbands x nchan with reverberation times) tfit, lfit, dchr, lvalues are
    the outputs of revtime (see) for each band. Band 0 is wideband (fc = 1)
    '''
    # if bankname is None, perform wideband
    # option to skip A-weighting filter
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
        fs = int(fbank['fs'])
        print('Using sample rate from filter bank:' + str(fs))
    else:
        raise TypeError('Input must be ndarray or filename')    
    if data.ndim == 1:
        data = data[:,np.newaxis] # array must be 2D
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
    ndir = find_dir(data, pw=1.0,fs=fs)
    #print(int(tnoise*fs))
    #print(data.shape)
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

def direct_to_reverb(data, nmax, ndir=None, pw=1.0, fs=48000, s=6.0):
    '''
    Compute the direct-to-reverberant energy ratio (DRR) for the given signal data.
    '''
    if data.ndim == 1:
        data = data[:, np.newaxis]  # array must be 2D
    nsamples,nchan = data.shape
    nmax = int(np.minimum(nmax, nsamples))

    if ndir is None:
        ndir = find_dir(data, pw=pw, fs=fs)  # assumed to return shape (2, nchan)
    EDIR = np.zeros(nchan, dtype=float)
    EREV = np.zeros(nchan, dtype=float)

    t = np.arange(nmax)
    for n in range(nchan):
        ndr = int(min(max(ndir[1, n], 0), nmax))  # clamp
        cross = sigmoid(t, ndr, s)   # 0 -> direct, 1 -> reverb (as in acoustics.py) :contentReference[oaicite:3]{index=3}
        x = data[:nmax, n]
        EDIR[n] = np.sum((x * (1.0 - cross))**2)
        EREV[n] = np.sum((x * cross)**2)

    # Aggregate across channels (typical DRR single number), but keep per-channel energies available
    EDIR_tot = np.sum(EDIR)
    EREV_tot = np.sum(EREV)
    return 10.0 * np.log10((EDIR_tot + eps) / (EREV_tot + eps))



def find_echoes(data, nechoes=10, pw=1.0, fs=48000):
    '''
    Find the echoes in the signal data
    '''
    nw = int(np.floor(0.5*pw*fs/1000))
    if data.ndim == 1:
        data = data[:,np.newaxis] # array must be 2D
    nsamples,nchan = np.shape(data)
    echoes = np.zeros((nechoes,2,nchan))
    amp = 1-np.exp(-np.square(np.linspace(-3.0,3.0,6*nw)))
    data_copy = np.copy(data)
    for n in range(nchan):
        for m in range(nechoes):
            n0 = np.argmax(np.abs(data_copy[:,n]))
            echoes[m,0,n] = n0/fs
            a = clamp(n0 - nw, 0, nsamples)
            b = clamp(n0 + nw, 0, nsamples)
            echoes[m,1,n] = np.mean(np.square(data[a:b,n]))
            c = clamp(n0 - 3*nw, 0, nsamples)
            d = clamp(n0 + 3*nw, 0, nsamples)
            data_copy[c:d,n] *= amp[:(d-c)]  # windowed attenuation
    return echoes

def irstats(ir, window=0.01, overlap=0.005, fs=48000):
    if type(ir) is str:
        fs, data = wavfile.read(ir + '.wav')
    elif type(ir) is np.ndarray:
        data = ir
    else:
        raise TypeError('Input must be ndarray or filename')    
    if data.ndim == 1:
        data = data[:,np.newaxis] # array must be 2D
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
        std_safe = np.maximum(pars['std'][:, n], eps)
        stdb_raw = 10.0 * np.log10(std_safe)
        win = 51
        if win > len(stdb_raw):
            win = len(stdb_raw) if (len(stdb_raw) % 2 == 1) else max(1, len(stdb_raw) - 1)
        if win >= 5:
            stdb = signal.savgol_filter(stdb_raw, win, 3, axis=0)
        else:
            stdb = stdb_raw
        pars['stdbup'][:,n] = stdb - np.nanmin(stdb)
    nnoise = np.argmax(pars['stdbup']<stdbup_confidence,axis=0)    
    pars['tnoise'][0,:] = pars['tframe'][nnoise][:,0]
    return pars    

# echo density
#
#def find_modes # find modes up to a frequency

#def sti # speech intelligibility
    
#def spatial # lateral energy fraction




