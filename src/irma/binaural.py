import numpy as np
from .generate import sigmoid
from scipy import signal
from scipy.io import wavfile
from scipy.interpolate import interp1d
from scipy.fft import next_fast_len, rfft, fft, ifft
from numpy.fft.helper import rfftfreq

def fast_ccf(x1,x2):
    wav_len = x1.shape[0]
    wf = np.hanning(wav_len)
    x1 = x1*wf
    x2 = x2*wf
    X1 = fft(x1,2*wav_len-1)# equivalent to add zeros
    X2 = fft(x2,2*wav_len-1)
    ccf_unshift = np.real(ifft(np.multiply(X1,np.conjugate(X2))))
    ccf = np.concatenate([ccf_unshift[wav_len:],ccf_unshift[:wav_len]],axis=0)
    return ccf

def get_ITD(x,fs,max_delay=None,inter_method='parabolic'):
    wav_len = x.shape[0]
    x_detrend = x
    if max_delay == None:
        max_delay = int(1e-3*fs)
    ccf_full = fast_ccf(x_detrend[:,0],x_detrend[:,1])
    ccf = ccf_full[wav_len-1-max_delay:wav_len+max_delay]
    ccf_std = ccf/(np.sqrt(np.sum(x_detrend[:,0]**2)*np.sum(x_detrend[:,1]**2)))
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

def get_ILD(x):
  return 10*np.log10(np.sum(x[:,1]**2)/np.sum(x[:,0]**2)+1e-10)

def lbinaural(data,dt,eref=1.0):
  # calcula la intensidad binaural de la senal xb de dos canales
  el = np.sum(np.sum(np.square(data[:,0])))*dt
  er = np.sum(np.sum(np.square(data[:,1])))*dt
  return 10*np.log10(np.sqrt(el*er)/eref)

def lbinaural_dr(data,ndr,dt,s=1,eref=1.0):
  # data senal binaural, ndr numero se sample que separa el d/r, dt, el paso temporal, s pendiente de la sigmoidea
  N, _ = data.shape
  cross = sigmoid(np.arange(N),ndr,s)
  Ltot = lbinaural(data,dt,eref)
  Ldir = lbinaural(data*(1-cross[:,np.newaxis]),dt,eref)
  Lrev = lbinaural(data*cross[:,np.newaxis],dt,eref)
  return Ltot,Ldir,Lrev

def iacc_dr(data,ndr,fs):
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
    # devuelve la hrtf binned para la senal data
    # data senal binaural, ndr numero se sample que separa el d/r
    N, _ = np.shape(data)
    cross = sigmoid(np.arange(N),ndr,2)
    lfreq = fmin*np.logspace(0,np.log2(fmax/fmin),nbins,base=2)
    freq = rfftfreq(N,d = 1/fs)
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




def spectral_centroid_dr(data,ndr,s=2,fmin=20,fmax=20000,fs=48000, average_channels=True):
    N, nchan = np.shape(data)
    SC_dir = np.zeros(nchan)
    SC_rev = np.zeros(nchan)
    SC_tot = np.zeros(nchan)
    freq = rfftfreq(N,d = 1/fs)
    nf = np.argmax(freq>fmax)
    ni = np.argmax(freq>fmin)
    cross = sigmoid(np.arange(N),ndr,s)
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
    # devuelve la varianza espectral total del directo y del reverberante entre fmin y fmax
    # xb senal binaural, ndr numero se sample que separa el d/r, dt, el paso temporal, s pendiente de la sigmoidea
    N, nchan = np.shape(data)
    SV_dir = np.zeros(nchan)
    SV_rev = np.zeros(nchan)
    SV_tot = np.zeros(nchan)
    freq = rfftfreq(N,d = 1/fs)
    nf = np.argmax(freq>fmax)
    ni = np.argmax(freq>fmin)
    cross = sigmoid(np.arange(N),ndr,s)
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
    