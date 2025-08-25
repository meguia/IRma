import numpy as np
from .generate import sigmoid
from .process import fast_ccf, find_dir
from scipy import signal
from scipy.fft import rfft, rfftfreq

###########################################
# ACOUSTIC PARAMETERS


#############################################
# BINAURAL
# Here the input is always data(nsamples,2) for a single binaural channel

def get_ITD(data,fs,max_delay=None,inter_method='parabolic'):
    '''
    Compute the interaural time difference (ITD) of the binaural signal.
    '''
    wav_len = data.shape[0]
    if max_delay == None:
        max_delay = int(1e-3*fs)
    ccf_full = fast_ccf(data[:,0],data[:,1])
    ccf = ccf_full[wav_len-1-max_delay:wav_len+max_delay]
    ccf_std = ccf/(np.sqrt(np.sum(data[:,0]**2)*np.sum(data[:,1]**2)))
    max_pos = np.argmax(ccf)
    delta = 0
    if inter_method == 'exponential':
        if max_pos> 0 and max_pos < max_delay*2-2:
            if np.min(ccf[max_pos-1:max_pos+2]) > 0:
                delta = (np.log(ccf[max_pos+1])-np.log(ccf[max_pos-1]))/\
                            (4*np.log(ccf[max_pos])-
                             2*np.log(ccf[max_pos-1])-
                             2*np.log(ccf[max_pos+1]))
    elif inter_method == 'parabolic':
        if max_pos> 0 and max_pos < max_delay*2-2:
            delta = (ccf[max_pos-1]-ccf[max_pos+1])/(2*(ccf[max_pos+1]-2*ccf[max_pos]+ccf[max_pos-1]))
    ITD = float((max_pos-max_delay-1+delta))/fs*1e3
    return [ITD,ccf_std]

def get_ILD(data):
  '''
  Compute the interaural level difference (ILD) of the binaural signal.
  '''
  return 10*np.log10(np.sum(data[:,1]**2)/np.sum(data[:,0]**2)+1e-10)


def lbinaural(data,dt,eref=1.0):
  '''
  Compute the binaural level of the signal.
  '''
  el = np.sum(np.sum(np.square(data[:,0])))*dt
  er = np.sum(np.sum(np.square(data[:,1])))*dt
  return 10*np.log10(np.sqrt(el*er)/eref)

def lbinaural_dr(data,ndr,dt,s=1,eref=1.0):
  '''
  Compute the binaural level difference (D/R) of the signal.
  ndr is the number of samples that separate the direct and reverberant sound.
  dt is the temporal resolution of the signal and s the slope of the sigmoid function.
  '''
  N, _ = data.shape
  cross = sigmoid(np.arange(N),ndr,s)
  Ltot = lbinaural(data,dt,eref)
  Ldir = lbinaural(data*(1-cross[:,np.newaxis]),dt,eref)
  Lrev = lbinaural(data*cross[:,np.newaxis],dt,eref)
  return Ltot,Ldir,Lrev

def iacc_dr(data,ndr,fs):
  '''
  Compute the interaural cross-correlation (IACC) for the direct and reverberant components.
  '''
  N, _ = data.shape # binaural
  nt = int(fs/1000) # 1 ms to each side
  # total
  cc = signal.correlate(data[:,0],data[:,1])
  norm = np.sqrt(np.sum(np.square(data[:,0]))*np.sum(np.square(data[:,1])))
  iacf_tot = cc[N-nt-1:N+nt-1]/norm
  # direct sound
  cc = signal.correlate(data[:ndr,0],data[:ndr,1])
  norm = np.sqrt(np.sum(np.square(data[:ndr,0]))*np.sum(np.square(data[:ndr,1])))
  iacf_dir = cc[ndr-nt-1:ndr+nt-1]/norm
  # reverberant
  cc = signal.correlate(data[ndr:,0],data[ndr:,1])
  norm = np.sqrt(np.sum(np.square(data[ndr:,0]))*np.sum(np.square(data[ndr:,1])))
  iacf_rev = cc[N-ndr-nt-1:N-ndr+nt-1]/norm
  return iacf_tot, iacf_dir, iacf_rev
  
def hrtf_binned(data,ndr,fmin=20,fmax=20000,fs=48000,nbins=50):
    '''
    Compute the binned HRTF for the given binaural signal.
    data is the binaural signal, ndr is the number of samples that separate the direct and reverberant sound.
    '''
    nsamples, _ = np.shape(data)
    cross = sigmoid(np.arange(nsamples),ndr,2)
    lfreq = fmin*np.logspace(0,np.log2(fmax/fmin),nbins,base=2)
    freq = rfftfreq(nsamples,d = 1/fs)
    nfreq = [np.argmax(freq>lf) for lf in lfreq]
    spL_tot = np.abs(rfft(data[:,:,0],axis=-1))
    cfreqL_tot = np.array([np.mean(spL_tot[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    spR_tot = np.abs(rfft(data[:,:,1],axis=-1))
    cfreqR_tot = np.array([np.mean(spR_tot[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    spL_dir = np.abs(rfft(data[:,0]*(1-cross),axis=-1))
    cfreqL_dir = np.array([np.mean(spL_dir[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    spR_dir = np.abs(rfft(data[:,1]*(1-cross),axis=-1))
    cfreqR_dir = np.array([np.mean(spR_dir[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    spL_rev = np.abs(rfft(data[:,0]*cross,axis=-1))
    cfreqL_rev = np.array([np.mean(spL_rev[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    spR_rev = np.abs(rfft(data[:,1]*cross,axis=-1))
    cfreqR_rev = np.array([np.mean(spR_rev[:,nfreq[n]:nfreq[n+1]],axis=-1) for n in range(len(nfreq)-1)])
    return cfreqL_tot,cfreqR_tot,cfreqL_dir,cfreqR_dir,cfreqL_rev,cfreqR_rev

###########################################################
# DIRECT TO REVERBERANT AND LEVEL FOR MULTICHANNEL data(nsamples, nchannels) signals

def level(data,fs,eref=1.0):
    '''
    Compute the overall sound level of a single channel signal.
    '''
    dt = 1/fs
    temp = np.sum(np.sum(np.square(data)))*dt
    return 10*np.log10(temp/eref) 

           
def drlevel_bands(data,bankname,ndr=None,s=2.0,eref=1.0,fs=48000):
    '''
    Compute the overall sound level of the signal for each band in the filter bank for the direct and reverberant components.
    data is the signal, ndr is the number of samples that separate the direct and reverberant sound.
    bankname is the name of the filter bank file (without extension).
    '''
    if ndr is None:
        ndir = find_dir(data, pw=0.5,fs=fs)
        ndr = ndir[1,:]
    nsamples, nchan = np.shape(data)
    fbank = np.load(bankname + '.npz')  
    nbands, _, _ = fbank['sos'].shape
    Ltot = np.zeros((nbands,nchan))
    Ldir = np.zeros((nbands,nchan))
    Lrev = np.zeros((nbands,nchan))
    for n in range(nchan):
        print(ndr[n])
        cross = sigmoid(np.arange(nsamples),ndr[n],s)
        direct = data[:,n]*(1-cross)
        reverb = data[:,n]*cross
        for m in range(nbands):
            data_filt = signal.sosfiltfilt(fbank['sos'][m], data[:,n], axis=0) 
            dir_filt = signal.sosfiltfilt(fbank['sos'][m], direct, axis=0) 
            rev_filt = signal.sosfiltfilt(fbank['sos'][m], reverb, axis=0) 
            Ltot[m,n] = level(data_filt,fs,eref)
            Ldir[m,n] = level(dir_filt,fs,eref)
            Lrev[m,n] = level(rev_filt,fs,eref)
    return Ltot,Ldir,Lrev

def spectral_centroid_dr(data,ndr,s=2,fmin=20,fmax=20000,fs=48000, average_channels=True):
    '''
    Compute the spectral centroid for the direct and reverberant components of the signal.
    '''
    nsamples, nchan = np.shape(data)
    SC_dir = np.zeros(nchan)
    SC_rev = np.zeros(nchan)
    SC_tot = np.zeros(nchan)
    freq = rfftfreq(nsamples,d = 1/fs)
    nf = np.argmax(freq>fmax)
    ni = np.argmax(freq>fmin)
    cross = sigmoid(np.arange(nsamples),ndr,s)
    for n in range(nchan):
        spec = np.abs(rfft(data[:,n]))
        SC_tot[n] = np.sum(spec[ni:nf]*freq[ni:nf])/np.sum(spec[ni:nf])
        spec = np.abs(rfft(data[:,n]*(1-cross)))
        SC_dir[n] = np.sum(spec[ni:nf]*freq[ni:nf])/np.sum(spec[ni:nf])
        spec = np.abs(rfft(data[:,n]*cross))
        SC_rev[n] = np.sum(spec[ni:nf]*freq[ni:nf])/np.sum(spec[ni:nf])
    if average_channels:
      return np.mean(SC_tot),np.mean(SC_dir),np.mean(SC_rev)
    else:
      return SC_tot,SC_dir,SC_rev  

def spectral_variance_dr(data,ndr,s=2,fmin=20,fmax=20000,fs=48000, average_channels=True):
    '''
    Compute the spectral variance for the direct and reverberant components of the signal.
    '''
    nsamples, nchan = np.shape(data)
    SV_dir = np.zeros(nchan)
    SV_rev = np.zeros(nchan)
    SV_tot = np.zeros(nchan)
    freq = rfftfreq(nsamples,d = 1/fs)
    nf = np.argmax(freq>fmax)
    ni = np.argmax(freq>fmin)
    cross = sigmoid(np.arange(nsamples),ndr,s)
    for n in range(nchan):
        spec = np.abs(rfft(data[:,n]))
        SV_tot[n] = np.var(20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf])))
        spec = np.abs(rfft(data[:,n]*(1-cross)))
        SV_dir[n] = np.var(20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf])))
        spec = np.abs(rfft(data[:,n]*cross))
        SV_rev[n] = np.var(20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf])))
    if average_channels:
      return np.sqrt(np.mean(SV_tot)),np.sqrt(np.mean(SV_dir)),np.sqrt(np.mean(SV_rev))
    else:
      return np.sqrt(SV_tot),np.sqrt(SV_dir),np.sqrt(SV_rev)
    