import yaml 
import datetime
from scipy.io import wavfile
from acousticfield.generate import sweep
from acousticfield.io import play_rec
from acousticfield.process import ir_extract

class RecordingSession:
    def __init__(self, session_id, speakers, microphones,speaker_pos=None,microphone_pos=None,
                 inchan=[0,1],outchan=[0,1],loopback=None,sampling_rate=48000,date=None,hour=None,
                 recordingpath=None,sweepfile=None,sweeprange=[30,22000],sweeprep=1,sweeppost=2.0,
                 sweepdur=10.0):
        self.session_id = session_id
        self.speakers = speakers
        self.microphones = microphones
        self.speaker_pos = speaker_pos or [0,0]
        self.microphone_pos = microphone_pos or [0,0]
        self.input_channels = inchan
        self.output_channels = outchan
        self.loopback = loopback
        self.sampling_rate = sampling_rate
        self.date = date or datetime.date.today().strftime("%Y-%m-%d")
        self.hour = hour or datetime.datetime.now().strftime("%H:%M:%S")
        self.comments = ""
        if sweepfile is None:
            srkhz = self.sampling_rate//1000
            maxrange = sweeprange[1]//1000
            sweepfile = f"sweep_x{sweeprep}_{srkhz}k_{int(sweepdur)}s_{sweeprange[0]}_{maxrange}k"
            print("generating sweep " + sweepfile)
            sweep(T=sweepdur,fs=self.sampling_rate,f1=sweeprange[0],f2=sweeprange[1],Nrep=sweeprep,
                  filename=sweepfile,post=sweeppost)
        self.sweepfile = sweepfile
        self.rpath = recordingpath or ""
        self.recordings = []

    def generate_audio_file_prefix(self, speaker, microphone, nchannels, loopback,type,take):
        prefix = f"{self.session_id}_S{self.speakers[speaker-1]}_M{self.microphones[microphone-1]}_"
        prefix += f"{nchannels}ch" 
        prefix += "_loop" if loopback is not None else ""
        prefix += f"_{type}" if type is not None else ""
        prefix += f"_({take})" if take>1 else ""
        return prefix

    def record_ir(self,speaker,microphone,type=None,loopback=None,take=1,comment=''):
        nchannels = len(self.output_channels)
        prefix = self.generate_audio_file_prefix(speaker, microphone, nchannels, loopback, type, take)
        print("Recording ... "+prefix)
        rec_temp = play_rec(self.sweepfile,self.rpath+'rec_'+prefix,chanin=self.input_channels,chanout=self.output_channels) 
        print("Extracting ---> "+prefix)
        ir_temp = ir_extract(rec_temp,self.sweepfile,self.rpath+'ri_'+prefix,loopback=loopback,fs=self.sampling_rate)
        self.recordings.append([prefix, comment])
        print("DONE")
        return ir_temp

    def list_recordings(self,comments=False):
        for n,recordings in enumerate(self.recordings):
            line = f"{n}:{recordings[0]}"
            if comments:
                line += f" -- {recordings[1]}"
            print(line)

    def load_ir(self,nrecording):
        if nrecording<len(self.recordings):
            _, data = wavfile.read(self.rpath+'ri_'+self.recordings[nrecording][0]+'.wav')
            return data
        else:
            raise ValueError("recording out of range")     

    def generate_backup_file_prefix(self):
        return f"{self.session_id}_backup"
    
    def add_comment(self,nrecording=None):
        if nrecording is None:
            new_comment = input("Enter a comment for session: ")
            self.comments += f"\n{new_comment}"
        else:    
            if nrecording<len(self.recordings):
                new_comment = input("Enter a comment for recording "+self.recordings[nrecording][0])
                self.recordings[nrecording][1]+= f"\n{new_comment}"
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
            'date': self.date,
            'hour': self.hour,
            'comments': self.comments,
            'sweepfile': self.sweepfile,
            'recording_path': self.rpath,
            'recordings': self.recordings
        }
        with open(filename, 'w') as file:
            yaml.dump(metadata, file)

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
        date = metadata.get('date')
        hour = metadata.get('hour')
        comments = metadata.get('comments', '')
        sweepfile = metadata.get('sweepfile')
        recordingpath = metadata.get('recording_path')
        recordings = metadata.get('recordings', [])
        session = RecordingSession(session_id, speakers, microphones, speaker_pos, microphone_pos,
                                   inchan, outchan, loopback, sampling_rate, date, hour,
                                   recordingpath, sweepfile)
        session.comments = comments
        session.recordings = recordings
        return session    