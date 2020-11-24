import numpy as np
from scipy import signal

def timewindow(spec,tstep):
    ts = np.arange(0,spec['nt']-tstep,tstep)
    nts = len(ts)
    ts += tstep//2    
    return ts,spec['t'][ts],nts


def acoustic_complexity(spec,tstep):
    ts,t,nts = timewindow(spec,tstep)
    ACI = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        subspecs = [np.array(spec['s'][n,:,t0:t0+tstep]) for t0 in ts]
        ACI[n,:] = [np.sum((np.sum(abs(np.diff(subspec)), axis=1) / np.sum(subspec, axis=1))) for subspec in subspecs] 
    return t, ACI
    
    
def bioacoustic_index(spec, tstep, frange=[2000,8000]):
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    ts,t,nts = timewindow(spec,tstep)
    f_bin = [int(np.around(a/spec['df'])) for a in frange]
    BI = np.zeros((spec['nchan'],nts)) 
    for n in np.arange(spec['nchan']):
        spec_BI = 20*np.log10(spec['s'][n,:]/np.max(spec['s']))
        spec_BI_mean = np.array([10*np.log10(np.mean(np.power(10,(spec_BI[:,t0:t0+tstep]/10)), axis=1))for t0 in ts])
        spec_BI_mean_segment =  spec_BI_mean[:,f_bin[0]:f_bin[1]]
        spec_BI_mean_segment_normalized = spec_BI_mean_segment - np.min(spec_BI_mean_segment)
        BI[n,:] = np.sum(spec_BI_mean_segment_normalized/spec['df'],axis=1)
    return t,BI

def spectral_entropy(spec, tstep):
    """
    Computes Spectral entropy of Shannon from spectrogram spect
    """
    ts,t,nts = timewindow(spec,tstep)
    N = spec['nf']
    HS = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        spec_av =  np.array([np.sum(spec['s'][n,:,t0:t0+tstep],axis=-1) for t0 in ts])
        spec_avav = np.sum(spec_av,axis=-1)
        spec_av /= spec_avav[:,np.newaxis]
        HS[n,:] = -np.sum([y*np.log2(y) for y in spec_av],axis=1)/np.log2(N)
    return t,HS

def ndsi(spec, tstep, anthrophony=[1000,2000], biophony=[2000,11000]):
    """
    Computes NDSI Using Spectrogram 
    """
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    ts,t,nts = timewindow(spec,tstep)
    anthro_bin = [int(np.around(a/spec['df'])) for a in anthrophony]
    bio_bin = [int(np.around(a/spec['df'])) for a in biophony]
    ndsi = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        anthro = np.array([np.sum(spec['s'][n,anthro_bin[0]:anthro_bin[1],t0:t0+tstep])for t0 in ts])
        bio = np.array([np.sum(spec['s'][n,bio_bin[0]:bio_bin[1],t0:t0+tstep]) for t0 in ts])
        ndsi[n,:] = (bio-anthro)/(bio+anthro)
      
    return t,ndsi
    
def gini(values):
    """
    Compute the Gini index of values.
    """
    y = sorted(values)
    n = len(y)
    G = np.sum([i*j for i,j in zip(y,range(1,n+1))])
    G = 2 * G / np.sum(y) - (n+1)
    return G/n

def acoustic_evenness(spec, tstep, max_freq=10000, db_threshold = -50, freq_step=1000):
    """
    Compute the Acoustic Evenness Index AEI
    """
    ts,t,nts = timewindow(spec,tstep)
    bands_Hz = range(0, max_freq, freq_step)
    bands_bin = [f / spec['df'] for f in bands_Hz]
    AEI = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        subspecs = [np.array(spec['s'][n,:,t0:t0+tstep]) for t0 in ts]
        spec_AEI = np.array([20*np.log10(s/np.max(s)) for s in subspecs])
        spec_AEI_bands = [spec_AEI[:,int(bands_bin[k]):int(bands_bin[k]+bands_bin[1]),] for k in range(len(bands_bin))]
        values = [np.array([np.sum(spec_AEI_bands[k][t0,:,:]>db_threshold)/float(spec_AEI_bands[k][t0,:,:].size) for k in range(len(bands_bin))]) for t0 in range(nts)]
        AEI[n,:] = [gini(values[n]) for n in range(nts)]

    return t, AEI       