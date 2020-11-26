import numpy as np
from scipy import signal
from scipy.interpolate import interp1d

def load_pcm(file,nchan,nbytes=4):
    """
    Function to load a raw PCM audio file with nchan channels and nbytes little endian
    """
    data=np.memmap(file, dtype='u1', mode='r')
    nsamples=data.shape[0]//(nchan*nbytes)
    if nbytes==4:
        realdata=np.reshape(data.view(np.int32),(nsamples,nchan))
    elif nbytes==2:
        realdata=np.reshape(data.view(np.int16),(nsamples,nchan))
    elif nbytes==1:
        realdata=np.reshape(data.view(np.int8),(nsamples,nchan))
    else:
        raise Exception("Only 4,2 or 1 bytes allowed")
    return realdata

def spectrogram(data, windowSize=512, overlap=None, fs=48000, windowType='hanning', normalized=False, logf=False):
    """
    Computa el espetrograma de la senal data
    devuelve spec un diccionario con keys 
    """
    #force to power of two
    windowSize = np.power(2,int(np.around(np.log2(windowSize))))
    if overlap is None:
        overlap = windowSize//8
    if data.ndim == 1:
        data = data[:,np.newaxis] # el array debe ser 2D
    nsamples, nchan = np.shape(data)
    nt = int(np.ceil((nsamples-windowSize)/(windowSize-overlap)))
    # Dict for spectrogram
    listofkeys = ['nchan','f','t','s','nt','nf','df','window','type','overlap','log']
    spec = dict.fromkeys(listofkeys,0 )
    spec['nchan'] = nchan
    spec['nf'] = windowSize//2+1
    spec['s'] = np.zeros((nchan,spec['nf'],nt))
    spec['window'] = windowSize
    spec['type'] = windowType
    spec['overlap'] = overlap
    spec['logf'] = logf
    spec['nt'] = nt
    for n in np.arange(nchan):       
        f,t,spectro = signal.spectrogram(data[:,n], fs, window=windowType, nperseg=windowSize, noverlap=overlap)
        spec['t'] = t
        spec['df'] = f[1]
        print(spectro.shape)
        if logf:
            lf = np.power(2,np.linspace(np.log2(f[1]),np.log2(f[-1]),spec['nf']))
            fint = interp1d(f,spectro.T,fill_value="extrapolate")
            spec['f'] = lf
            spec['s'][n] = fint(lf).T
        else:
            spec['f'] = f
            spec['s'][n] = spectro
    if normalized:
        spec['s'] = spec['s']/np.max(spec['s'])    
    return spec        

def subspecs(spec,tstep,overlap=0.5):
    """
    Creates subspectrograms from spec of window size tstep/(1-overlap) with time step tstep
    """
    twin = int(np.around(tstep/(1-overlap)))
    ts = np.arange(0,spec['nt']-twin,tstep)
    subs = np.array([spec['s'][:,:,t0:t0+twin] for t0 in ts])
    ts += twin//2    
    return subs.swapaxes(0,1),spec['t'][ts]


def acoustic_complexity(spec,tstep):
    subspec,t = subspecs(spec,tstep)
    ACI = np.sum(np.sum(np.diff(subspec),axis=-1)/np.sum(subspec[0],axis=-1),axis=-1)
    return t, ACI
    
    
def bioacoustic_index(spec, tstep, frange=[2000,8000]):
    if spec['logf']:
        raise ValueError('NDSI compute for linear frequency only')
    subspec,t = subspecs(spec,tstep)
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
    n = values.shape[ax]
    idx = np.arange(1, n+1).reshape(-1,1)*np.ones_like(values)
    G = np.sum(values*idx,axis=ax)
    G = 2*G/np.sum(values,axis=ax) - (n+1)
    return G/n

def acoustic_diversity_even(spec, tstep, max_freq=10000, db_threshold = -50, freq_step=1000):
    """
    Compute the Acoustic Evenness Index AEI and Acoustic Diversity Index ADI
    """
    subspec,t = subspecs(spec,tstep)
    bands_Hz = range(0, max_freq, freq_step)
    bands_bin = [int(np.around(f / spec['df'])) for f in bands_Hz]
    spec_AEI = 20*np.log10(subspec/np.amax(subspec,axis=(-2,-1))[...,np.newaxis,np.newaxis])
    spec_AEI_bands = np.array([spec_AEI[:,:,bb:bb+bands_bin[1],:] for bb in bands_bin])
    val = np.average(spec_AEI_bands>db_threshold,axis=(-2,-1)).swapaxes(0,1)
    AEI = gini(val,ax=1)
    tol = 1e-8
    val[val<tol]=tol
    ADI = np.sum(-val/np.sum(val,axis=(0,1))*np.log(val/np.sum(val,axis=(0,1))),axis=1)
    return t, AEI, ADI       


def indices(spec,tstep,ACI=True,BI=True,NDSI=True,AEI=True,ADI=True,HS=True,HT=True,H=True,
            fbi=[2000,8000],fanthro=[1000,2000], fbio=[2000,11000],max_f=10000, db_thresh = -50, f_step=1000):
    """
    Compute ALL indices
    """
    listofkeys = ['nchan','t','aci','bi','ndsi','aei','adi','hs','ht','h']
    ind = dict.fromkeys(listofkeys,0)
    subspec,t = subspecs(spec,tstep)
    ind['t']=t
    ind['nchan']=spec['nchan']
    spec_norm = subspec/np.amax(subspec,axis=(-2,-1))[...,np.newaxis,np.newaxis]
    if ACI:
        ind['aci'] = np.sum(np.sum(np.diff(subspec),axis=-1)/np.sum(subspec[0],axis=-1),axis=-1)
    if BI:
        f_bin = [int(np.around(a/spec['df'])) for a in fbi]
        spec_mean = 10*np.log10(np.mean(np.square(spec_norm), axis=-1))
        spec_mean_segment =  spec_mean[...,f_bin[0]:f_bin[1]]
        spec_mean_segment_norm = spec_mean_segment - np.min(spec_mean_segment)
        ind['bi'] = np.sum(spec_mean_segment_norm/spec['df'],axis=-1) 
    if NDSI:
        anthro_bin = [int(np.around(a/spec['df'])) for a in fanthro]
        bio_bin = [int(np.around(a/spec['df'])) for a in fbio]
        anthro = np.sum(subspec[:,:,anthro_bin[0]:anthro_bin[1],:],axis=(-2,-1))
        bio = np.sum(subspec[:,:,bio_bin[0]:bio_bin[1],:],axis=(-2,-1))
        ind['ndsi'] = (bio-anthro)/(bio+anthro)
    if HS:
        spec_av =  np.sum(subspec,axis=-1)
        spec_av /= np.sum(spec_av,axis=-1)[...,np.newaxis]
        ind['hs'] = -np.sum(spec_av*np.log2(spec_av),axis=-1)/np.log2(spec['nf'])    
    if AEI or ADI:
        bands_Hz = range(0, max_f, f_step)
        bands_bin = [int(np.around(f / spec['df'])) for f in bands_Hz]
        spec_AEI = 20*np.log10(spec_norm)
        spec_AEI_bands = np.array([spec_AEI[:,:,bb:bb+bands_bin[1],:] for bb in bands_bin])
        val = np.average(spec_AEI_bands>db_thresh,axis=(-2,-1)).swapaxes(0,1)
        if AEI:
            ind['aei']=gini(val,ax=1)
        if ADI:
            tol = 1e-8
            val[val<tol]=tol
            ind['adi'] = np.sum(-val/np.sum(val,axis=(0,1))*np.log(val/np.sum(val,axis=(0,1))),axis=1)
    return ind





