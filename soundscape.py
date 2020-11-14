import numpy as np

def acoustic_complexity(spec,tstep):
    ts = np.arange(0,spec['nt']-tstep,tstep)
    nts = len(ts)
    aci = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        subspecs = [np.array(spec['s'][n,:,t0:t0+tstep]) for t0 in ts]
        aci[n,:] = [np.sum((np.sum(abs(np.diff(subspec)), axis=1) / np.sum(subspec, axis=1))) for subspec in subspecs] 
    ts += tstep//2    
    return spec['t'][ts], aci
    
    
def bioacoustic_index(spec, tstep, frange=[2000,8000]):
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    ts = np.arange(0,spec['nt']-tstep,tstep)
    nts = len(ts)
    df = spec['f'][1]
    f_bin = [int(np.around(a/df)) for a in frange]
    BI = np.zeros((spec['nchan'],nts)) 
    for n in np.arange(spec['nchan']):
        spec_BI = 20*np.log10(spec['s'][n,:]/np.max(spec['s']))
        spec_BI_mean = np.array([10*np.log10(np.mean(np.power(10,(spec_BI[:,t0:t0+tstep]/10)), axis=1))for t0 in ts])
        spec_BI_mean_segment =  spec_BI_mean[:,f_bin[0]:f_bin[1]]
        spec_BI_mean_segment_normalized = spec_BI_mean_segment - np.min(spec_BI_mean_segment)
        BI[n,:] = np.sum(spec_BI_mean_segment_normalized/df,axis=1)
    return spec['t'][ts],BI

def spectral_entropy(spect):
    return

def temporal_entropy(spect):
    return

def ndsi(spec, tstep, anthrophony=[1000,2000], biophony=[2000,11000]):
    """
    Computes NDSI Using Spectrogram 
    """
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    ts = np.arange(0,spec['nt']-tstep,tstep)
    nts = len(ts)
    df = spec['f'][1]
    anthro_bin = [int(np.around(a/df)) for a in anthrophony]
    bio_bin = [int(np.around(a/df)) for a in biophony]
    ndsi = np.zeros((spec['nchan'],nts))
    for n in np.arange(spec['nchan']):
        anthro = np.array([np.sum(spec['s'][n,anthro_bin[0]:anthro_bin[1],t0:t0+tstep])for t0 in ts])
        bio = np.array([np.sum(spec['s'][n,bio_bin[0]:bio_bin[1],t0:t0+tstep]) for t0 in ts])
        ndsi[n,:] = (bio-anthro)/(bio+anthro)
      
    return spec['t'][ts],ndsi
    
def gini(values):
    """
    Compute the Gini index of values.
    """
    y = sorted(values)
    n = len(y)
    G = np.sum([i*j for i,j in zip(y,range(1,n+1))])
    G = 2 * G / np.sum(y) - (n+1)
    return G/n
    