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

def lbinaural(xb,dt,eref=1.0):
  # calcula la intensidad binaural de la senal xb de dos canales
  el = np.sum(np.sum(np.square(xb[:,0])))*dt
  er = np.sum(np.sum(np.square(xb[:,1])))*dt
  return 10*np.log10(np.sqrt(el*er)/eref)

def lbinaural_dr(xb,ndr,dt,s=1,eref=1.0):
  # xb senal binaural, ndr numero se sample que separa el d/r, dt, el paso temporal, s pendiente de la sigmoidea
  N, _ = xb.shape
  cross = sigmoid(np.arange(N),ndr,s)
  Ltot = lbinaural(xb,dt,eref)
  Ldir = lbinaural(xb*(1-cross[:,np.newaxis]),dt,eref)
  Lrev = lbinaural(xb*cross[:,np.newaxis],dt,eref)
  return Ltot,Ldir,Lrev

def spectral_centroid_dr(data,ndr,s=2,fmin=20,fmax=20000,fs=48000):
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
        spec = np.abs(rfft(data[:,n])*(1-cross))
        SC_dir[n] = np.sum(spec[ni:nf]*freq[ni:nf])/np.sum(spec[ni:nf]*(1-cross))
        spec = np.abs(rfft(data[:,n])*cross)
        SC_rev[n] = np.sum(spec[ni:nf]*freq[ni:nf])/np.sum(spec[ni:nf]*cross)
    return SC_tot,SC_dir,SC_rev

def spectral_variance_dr(data,ndr,s=2,fmin=20,fmax=20000,fs=48000):
    # devuelve la varianza espectral total del directo y del reverberante entre fmin y fmax
    # xb senal binaural, ndr numero se sample que separa el d/r, dt, el paso temporal, s pendiente de la sigmoidea
    nchan = np.shape(data)
    SV_dir = np.zeros(nchan)
    SV_rev = np.zeros(nchan)
    SV_tot = np.zeros(nchan)
    freq = rfftfreq(N,d = 1/fs)
    nf = np.argmax(freq>fmax)
    ni = np.argmax(freq>fmin)
    cross = sigmoid(np.arange(N),ndr,s)
    for n in range(nchan):
        spec = np.abs(rfft(data[:,n]))
        il = 20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf]))
        SV_tot[n] = np.sqrt(np.var(il))
        spec = np.abs(rfft(data[:,n])*(1-cross))
        il = 20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf]))
        SV_dir[n] = np.sqrt(np.var(il))
        spec = np.abs(rfft(data[:,n])*cross)
        il = 20*np.log10(spec[ni:nf]/np.mean(spec[ni:nf]))
        SV_rev[n] = np.sqrt(np.var(il))
    return SV_tot,SV_dir,SV_rev
    