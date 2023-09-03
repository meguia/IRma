import os
import yaml 
import datetime
import numpy as np
from scipy.io import wavfile
from .generate import sweep
from .io import play_rec
from .process import ir_extract

class RecordingSession:
    def __init__(self, session_id, speakers=None, microphones=None,speaker_pos=None,microphone_pos=None,
                 inchan=[1,2],outchan=[1,2],loopback=None,sampling_rate=48000,rtype=None,
                 date=None,hour=None,recordingpath=None,sweepfile=None,sweeprange=[30,22000],
                 sweeprep=1,sweeppost=2.0,sweepdur=10.0):
        self.session_id = session_id
        self.speakers = speakers or [1]
        self.microphones = microphones or [1]
        self.speaker_pos = speaker_pos or [0,0]
        self.microphone_pos = microphone_pos or [0,0]
        self.input_channels = inchan
        self.output_channels = outchan
        self.loopback = loopback
        self.sampling_rate = sampling_rate
        self.rtype = rtype 
        self.date = date or datetime.date.today().strftime("%Y-%m-%d")
        self.hour = hour or datetime.datetime.now().strftime("%H:%M:%S")
        self.comments = ""
        self.saved = False
        if sweepfile is None:
            srkhz = self.sampling_rate//1000
            maxrange = sweeprange[1]//1000
            sweepfile = f"sweep_x{sweeprep}_{srkhz}k_{int(sweepdur)}s_{sweeprange[0]}_{maxrange}k"
            print("generating sweep " + sweepfile)
            sweep(T=sweepdur,fs=self.sampling_rate,f1=sweeprange[0],f2=sweeprange[1],Nrep=sweeprep,
                  filename=sweepfile,post=sweeppost)    
        self.sweep_file = sweepfile
        self.recording_path = recordingpath  or ""
        self.recordings = []

    def generate_audio_file_prefix(self, speaker, microphone, direction, nchannels,loopback,rtype,take,overwrite):
        prefix = f"{self.session_id}_S{speaker}_M{microphone}"
        prefix += f"_D{direction}" if direction is not None else ""
        prefix += f"_{nchannels}ch" 
        prefix += "_loop" if loopback is not None else ""
        prefix += f"_{rtype}" if rtype is not None else ""
        prefix += f"_({take})" if take>1 else ""
        # Check if same recording exists
        recnames = [line['filename'] for line in self.recordings]
        if prefix in recnames and not overwrite:
            raise ValueError(f"Name already exists please use take a different take number")
        return prefix

    def record_ir(self,speaker,microphone,direction=None,take=1,comment='',overwrite=False):
        if self.loopback:
            nchannels = len(self.input_channels)-1 
            chan_loop = self.input_channels.index(self.loopback)
        else:    
            nchannels =  len(self.input_channels)
            chan_loop = None
        valid = True
        prefix = self.generate_audio_file_prefix(speaker, microphone, direction, nchannels, self.loopback, self.rtype, int(take),overwrite)
        print("Recording ... "+prefix)
        rec_temp = play_rec(self.sweep_file,os.path.join(self.recording_path,'rec_'+prefix),chanin=self.input_channels,chanout=self.output_channels,fs=self.sampling_rate)
        rec_max = np.max(np.delete(rec_temp,chan_loop,axis=1)) if self.loopback is not None else np.max(rec_temp)
        print(f"Maximum sample value = {rec_max}")
        print(f"Extracting ---> {prefix} using sr = {self.sampling_rate}")
        ir_temp = ir_extract(rec_temp,self.sweep_file,os.path.join(self.recording_path,'ir_'+prefix),loopback=chan_loop,fs=self.sampling_rate)
        print(f"IR shape = {ir_temp.shape}")
        rec_dic = dict(
            spk=speaker,
            mic=microphone,
            dir=direction,
            take=take,
            valid=valid,
            filename=prefix,
            nchan=nchannels,
            comment=comment
        )
        self.recordings.append(rec_dic)
        print("DONE")
        return ir_temp

    def label_invalid(self,nrecording=None):
        if nrecording is None:
            nrecording = len(self.recordings)
        self.recordings[nrecording]['valid']=False

    def playrec_file(self,filename,speaker,microphone,direction=1,take=1,channel=0,dim=1.0,comment=''):
        nchannels = len(self.input_channels)
        fs, fplay = wavfile.read(filename+".wav")
        if fplay.ndim > 1:
            data = fplay[:,channel]
        else:    
            data = fplay   
        data = (dim*data)/float(np.max(np.abs(data)))    
        prefix = self.generate_audio_file_prefix(speaker, microphone, direction, nchannels, self.loopback, self.rtype, take)
        recfile = filename + "_" + prefix
        print(f"Recording Audio file {filename} in {recfile}")
        rec_temp = play_rec(data,os.path.join(self.recording_path,recfile),chanin=self.input_channels,chanout=self.output_channels,fs=fs) 
        print(f"Maximum sample value = {np.max(rec_temp)}")
        self.recordings.append([recfile, comment])

    def list_recordings(self,comments=False):
        for n,recordings in enumerate(self.recordings):
            line = f"{n}:{recordings['filename']}"
            if comments:
                line += f" -- {recordings['comment']}"
            print(line)

    def load_ir(self,nrecording,ftype="wav"):
        if nrecording<len(self.recordings):
            fname =os.path.join(self.recording_path,'ir_'+self.recordings[nrecording]['filename'])
            if ftype == "wav":
                _, data = wavfile.read(fname+'.wav')
                return data
            elif ftype == "npy":
                return np.load(fname+".npy")
            elif ftype == "npz":
                data = np.load(fname+".npz")
                return data['ir']
            else:
                TypeError("Type non existent, please select wav npy or npz")
        else:
            raise ValueError("recording out of range")
    
    def load_ir_list(self,indices,ftype="wav"):
        ir_list = []
        for nrecording in indices:
            ir_list.append(self.load_ir(nrecording,ftype))
        return ir_list

    def generate_backup_file_prefix(self):
        return f"{self.session_id}_backup"
    
    def add_comment(self,nrecording=None):
        if nrecording is None:
            new_comment = input("Enter a comment for session: ")
            self.comments += f"\n{new_comment}"
        else:    
            if nrecording<len(self.recordings):
                new_comment = input("Enter a comment for recording "+self.recordings[nrecording][0])
                self.recordings[nrecording]['comment']+= f"\n{new_comment}"
            else:
                raise ValueError("recording out of range") 

    def save_metadata(self, filename):
        metadata = {
            'session_id': self.session_id,
            'speakers': self.speakers,
            'microphones': self.microphones,
            'speaker_positions': self.speaker_pos,
            'microphone_positions': self.microphone_pos,
            'input_channels': self.input_channels,
            'output_channels': self.output_channels,
            'loopback': self.loopback,
            'sampling_rate': self.sampling_rate,
            'rtype': self.rtype,
            'date': self.date,
            'hour': self.hour,
            'comments': self.comments,
            'sweepfile': self.sweep_file,
            'recording_path': self.recording_path,
            'recordings': self.recordings,
            'saved': self.saved
        }
        with open(filename, 'w') as file:
            yaml.dump(metadata, file)
        self.saved = True    

    @staticmethod
    def load_metadata(filename):
        with open(filename, 'r') as file:
            metadata = yaml.load(file, Loader=yaml.FullLoader)
        session_id = metadata['session_id']
        speakers = metadata['speakers']
        microphones = metadata['microphones']
        speaker_pos = metadata.get('speaker_positions', [0, 0])
        microphone_pos = metadata.get('microphone_positions', [0, 0])
        inchan = metadata.get('input_channels', [0, 1])
        outchan = metadata.get('output_channels', [0, 1])
        loopback = metadata.get('loopback', None)
        sampling_rate = metadata.get('sampling_rate', 48000)
        rtype = metadata.get('rype',None)
        date = metadata.get('date')
        hour = metadata.get('hour')
        comments = metadata.get('comments', '')
        sweepfile = metadata.get('sweepfile')
        recordingpath = metadata.get('recording_path')
        recordings = metadata.get('recordings', [])
        session = RecordingSession(session_id, speakers, microphones, speaker_pos, microphone_pos,
                                   inchan, outchan, loopback, sampling_rate, rtype, date, hour,
                                   recordingpath, sweepfile)
        session.comments = comments
        session.recordings = recordings
        session.saved = metadata.get('saved', False)
        return session    
