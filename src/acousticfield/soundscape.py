import numpy as np
from scipy import signal
from scipy.interpolate import interp1d



def subspecs(spec,**kwargs):
    """
    Creates subspectrograms and subenvelopes from spec of window size tstep/(1-overlap) with time step tstep
    """
    halfwin = kwargs['half_window']
    nwin = kwargs['number_of_windows']
    envwin = halfwin*kwargs['windowSize']
    ts = np.linspace(halfwin,spec['nt']-halfwin,nwin,dtype='int')
    te = np.linspace(envwin,spec['env'].shape[1]-envwin,nwin,dtype='int')
    subs = np.array([spec['s'][:,:,t0-halfwin:t0+halfwin] for t0 in ts])
    subenv = np.array([spec['env'][:,t0-envwin:t0+envwin] for t0 in te])
    print(subs.shape)
    print(subenv.shape)
    print(spec['t'].shape)
    return subs.swapaxes(0,1),subenv.swapaxes(0,1),spec['t'][ts]

    
def gini(values,ax=0):
    """
    Compute the Gini index of values.
    """
    values.sort(axis=ax)
    n = values.shape[ax]
    idx = np.arange(1, n+1).reshape(-1,1)*np.ones_like(values)
    G = np.sum(values*idx,axis=ax)
    G = 2*G/np.sum(values,axis=ax) - (n+1)
    return G/n

def indices(spec,**kwargs):
    """
    Compute ALL indices
    """
    listofkeys = ['nchan','nsamples','t','aci','bi','ndsi','aei','adi','hs','ht','sc','db']
    ind = dict.fromkeys(listofkeys,0)
    subspec,subenv,t = subspecs(spec,**kwargs)
    ind['t']=t
    ind['nsamples'] = spec['nsamples']
    ind['nchan']=spec['nchan']
    pars = kwargs['Parameters']
    spec_norm = subspec/np.amax(subspec,axis=(-2,-1))[...,np.newaxis,np.newaxis]
    ind['sc'] = np.sum(subspec*spec['f'][...,np.newaxis],axis=(-2,-1))/np.sum(subspec,axis=(-2,-1))
    ind['db'] = 20*np.log10(np.mean(subenv,axis=-1))
    if 'ACI' in pars:
        ind['aci'] = np.sum(np.sum(np.abs(np.diff(subspec)),axis=-1)/np.sum(subspec[0],axis=-1),axis=-1)
    if 'BI' in pars:
        f_bin = [int(np.around(a/spec['df'])) for a in kwargs['freq_BI']]
        spec_mean = 10*np.log10(np.mean(np.square(spec_norm), axis=-1))
        spec_mean_segment =  spec_mean[...,f_bin[0]:f_bin[1]]
        spec_mean_segment_norm = spec_mean_segment - np.min(spec_mean_segment)
        ind['bi'] = np.sum(spec_mean_segment_norm/spec['df'],axis=-1) 
    if 'NDSI' in pars:
        anthro_bin = [int(np.around(a/spec['df'])) for a in kwargs['freq_anthro']]
        bio_bin = [int(np.around(a/spec['df'])) for a in kwargs['freq_bio']]
        anthro = np.sum(subspec[:,:,anthro_bin[0]:anthro_bin[1],:],axis=(-2,-1))
        bio = np.sum(subspec[:,:,bio_bin[0]:bio_bin[1],:],axis=(-2,-1))
        ind['ndsi'] = (bio-anthro)/(bio+anthro)
    if 'HS' in pars:
        spec_av =  np.sum(subspec,axis=-1)
        spec_av /= np.sum(spec_av,axis=-1)[...,np.newaxis]
        ind['hs'] = -np.sum(spec_av*np.log2(spec_av),axis=-1)/np.log2(spec['nf']) 
    if 'HT' in pars:
        subenv[subenv<kwargs['tol']]=kwargs['tol']
        subenv /= np.sum(subenv,axis=-1)[...,np.newaxis]
        ind['ht'] = -np.sum(subenv*np.log2(subenv),axis=-1)/np.log2(subenv.shape[-1])
    if 'AEI' in pars or 'ADI' in pars:
        bands_Hz = range(0, kwargs['max_freq'], kwargs['freq_step'])
        bands_bin = [int(np.around(f / spec['df'])) for f in bands_Hz]
        spec_AEI = 20*np.log10(spec_norm)
        spec_AEI_bands = np.array([spec_AEI[:,:,bb:bb+bands_bin[1],:] for bb in bands_bin])
        val = np.average(spec_AEI_bands>kwargs['db_threshold'],axis=(-2,-1)).swapaxes(0,1)
        if 'AEI' in pars:
            ind['aei']=gini(val,ax=1)
        if 'ADI' in pars:
            val[val<kwargs['tol']]=kwargs['tol']
            ind['adi'] = np.sum(-val/np.sum(val,axis=(0,1))*np.log(val/np.sum(val,axis=(0,1))),axis=1)
    return ind





