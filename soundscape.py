import numpy as np
from scipy import signal

def subspecs(spec,tstep):
    ts = np.arange(0,spec['nt']-tstep,tstep)
    nts = len(ts)
    subs = np.array([spec['s'][:,:,t0:t0+tstep] for t0 in ts])
    ts += tstep//2    
    return subs.swapaxes(0,1),spec['t'][ts],nts


def acoustic_complexity(spec,tstep):
    subspec,t,nts = subspecs(spec,tstep)
    ACI = np.sum(np.sum(np.diff(subspec),axis=-1)/np.sum(subspec[0],axis=-1),axis=-1)
    return t, ACI
    
    
def bioacoustic_index(spec, tstep, frange=[2000,8000]):
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    subspec,t,nts = subspecs(spec,tstep)
    f_bin = [int(np.around(a/spec['df'])) for a in frange]
    spec_norm = subspec/np.amax(subspec,axis=(-2,-1))[...,np.newaxis,np.newaxis]
    spec_mean = 10*np.log10(np.mean(np.square(spec_norm), axis=-1))
    spec_mean_segment =  spec_mean[...,f_bin[0]:f_bin[1]]
    spec_mean_segment_norm = spec_mean_segment - np.min(spec_mean_segment)
    BI = np.sum(spec_mean_segment_norm/spec['df'],axis=-1)
    return t,BI

def spectral_entropy(spec, tstep):
    """
    Computes Spectral entropy of Shannon from spectrogram spect
    """
    subspec,t = subspecs(spec,tstep)
    spec_av =  np.sum(subspec,axis=-1)
    spec_av /= np.sum(spec_av,axis=-1)[...,np.newaxis]
    HS = -np.sum(spec_av*np.log2(spec_av),axis=-1)/np.log2(spec['nf'])
    return t,HS

def ndsi(spec, tstep, anthrophony=[1000,2000], biophony=[2000,11000]):
    """
    Computes NDSI Using Spectrogram 
    """
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    subspec,t = subspecs(spec,tstep)
    anthro_bin = [int(np.around(a/spec['df'])) for a in anthrophony]
    bio_bin = [int(np.around(a/spec['df'])) for a in biophony]
    anthro = np.sum(subspec[:,:,anthro_bin[0]:anthro_bin[1],:],axis=(-2,-1))
    bio = np.sum(subspec[:,:,bio_bin[0]:bio_bin[1],:],axis=(-2,-1))
    ndsi = (bio-anthro)/(bio+anthro)  
    return t,ndsi
    
def gini(values,ax=0):
    """
    Compute the Gini index of values.
    """
    values.sort(axis=ax)
    n = values.shape[0]
    G = np.sum([i*j for i,j in zip(values,range(1,n+1))])
    #G = 2 * G / np.sum(y) - (n+1)
    return G/n

def acoustic_evenness(spec, tstep, max_freq=10000, db_threshold = -50, freq_step=1000):
    """
    Compute the Acoustic Evenness Index AEI
    """
    subspec,t = subspecs(spec,tstep)
    bands_Hz = range(0, max_freq, freq_step)
    bands_bin = [f / spec['df'] for f in bands_Hz]
    spec_AEI = 20*np.log10(subspec/np.amax(subspec,axis=(-2,-1))[...,np.newaxis,np.newaxis])
    spec_AEI_bands = np.array([spec_AEI[:,:,bb:bb+bands_bin[1],:] for bb in bands_bin])
    values = np.average(spec_AEI_bands>db_threshold,axis=(-2,-1))
    AEI = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        #subspecs = [np.array(spec['s'][n,:,t0:t0+tstep]) for t0 in ts]
        spec_AEI = np.array([20*np.log10(s/np.max(s)) for s in subspecs])
        spec_AEI_bands = [spec_AEI[:,int(bands_bin[k]):int(bands_bin[k]+bands_bin[1]),] for k in range(len(bands_bin))]
        values = [np.array([np.sum(spec_AEI_bands[k][t0,:,:]>db_threshold)/float(spec_AEI_bands[k][t0,:,:].size) for k in range(len(bands_bin))]) for t0 in range(nts)]
        AEI[n,:] = [gini(values[n]) for n in range(nts)]

    return t, AEI       

def acoustic_diversity(spec, tstep, max_freq=10000, db_threshold = -50, freq_step=1000):
