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
    
    
def bioacoustic_index(spect, f, fmin=1000, fmax=8000):
    
    return

def spectral_entropy(spect):
    return

def temporal_entropy(spect):
    return

def ndsi(spec, tstep, anthrophony=[1000,2000], biophony=[2000,11000]):
    """
    Using Spectrogram
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
    

    