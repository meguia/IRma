import customtkinter as ctk
from yaml import safe_load
import sounddevice as sd
from .generate import sweep
from .session import RecordingSession
from .utils.ctktable import CTkTable
# las variables de la interfaz son siempre string y las de la clase RecordingSession 
# son del tipo que corresponde, con lo cual hay que convertir una en otra al guardar o cargar

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("dark-blue")  
fs = 48000 # default despues poner en menu

class GenerateWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x800")
        self.label = ctk.CTkLabel(self, text="Generate Log Sweep")
        self.label.grid(row=0,column=0,padx=20, pady=20)
        
        self.label_fmin = ctk.CTkLabel(self, text="fmin")
        self.label_fmin.grid(row=1,column=0,padx=20, pady=20)
        self.sweep_fmin_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=20))
        self.sweep_fmin_entry.grid(row=1,column=1,padx=20, pady=20)

        self.label_fmax = ctk.CTkLabel(self, text="fmax")
        self.label_fmax.grid(row=2,column=0,padx=20, pady=20)
        self.sweep_fmax_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=20000))
        self.sweep_fmax_entry.grid(row=2,column=1,padx=20, pady=20)

        self.label_post = ctk.CTkLabel(self, text="duration")
        self.label_post.grid(row=3,column=0,padx=20, pady=20)
        self.sweep_dur_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=10.0)) # en segundos
        self.sweep_dur_entry.grid(row=3,column=1,padx=20, pady=20) 

        self.label_post = ctk.CTkLabel(self, text="post")
        self.label_post.grid(row=4,column=0,padx=20, pady=20)   
        self.sweep_post_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=1.0)) # en segundos
        self.sweep_post_entry.grid(row=4,column=1,padx=20, pady=20)

        self.label_rep = ctk.CTkLabel(self, text="repetitions")
        self.label_rep.grid(row=5,column=0,padx=20, pady=20)
        self.sweep_rep_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=1)) 
        self.sweep_rep_entry.grid(row=5,column=1,padx=20, pady=20)

        self.generate_button = ctk.CTkButton(self, text="Generate", command=self.generate)
        self.generate_button.grid(row=6,column=0,padx=20, pady=20)

    def generate(self):
        self.sweep_fmin = int(self.sweep_fmin_entry.get())
        self.sweep_fmax = int(self.sweep_fmax_entry.get())
        self.sweep_dur = float(self.sweep_dur_entry.get())
        self.sweep_post = float(self.sweep_post_entry.get())
        self.sweep_rep = int(self.sweep_rep_entry.get())
        self.sampling_rate = 48000

        srkhz = self.sampling_rate//1000
        maxrange = self.sweep_fmax//1000
        self.sweepfile = f"sweep_x{self.sweep_rep}_{srkhz}k_{int(self.sweep_dur)}s_{self.sweep_fmin}_{maxrange}k"
        print("generating sweep " + self.sweepfile)
        sweep(T=self.sweep_dur,fs=self.sampling_rate,f1=self.sweep_fmin,f2=self.sweep_fmax,Nrep=self.sweep_rep,
        filename=self.sweepfile,post=self.sweep_post)

class Acousticfield_ctk():
    def __init__(self):
        self.root = ctk.CTk()
        self.save_and_close = False
        # configure window
        self.root.title("ACOUSTIC FIELD")
        self.root.geometry(f"{1200}x{600}")
        self.root.minsize(600, 400)
        #self.root.iconbitmap("src/acousticfield/icon.ico")
        #self.root.protocol("WM_DELETE_WINDOW", self.root.close_event)
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
    
        # initialization
        self.void_recording_session()
        self.audio_init(fs=fs)
        # configure grid layout (4x4)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.toplevel_window = None
        self.create_widgets()

    def create_widgets(self):
        # create sidebar frame with widgets
        fbig = ctk.CTkFont(family="Roboto", size=32)
        fnorm = ctk.CTkFont(family="Roboto", size=20)
        fsmall = ctk.CTkFont(family="Roboto", size=14)
        self.sidebar_frame = ctk.CTkFrame(self.root, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Session", font=fsmall)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20,0))
        self.sidebar_label_1 = ctk.CTkLabel(self.sidebar_frame, text=self.session_id, font=fbig)
        self.sidebar_label_1.grid(row=1, column=0, padx=20, pady=(20, 10))
        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Create",font=fnorm,command=self.create_recording_session)
        self.sidebar_button_1.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Load",command=self.load_recording_session)
        self.sidebar_button_2.grid(row=3, column=0, padx=20, pady=10)
        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Clean",command=self.clean_recording_session)
        self.sidebar_button_3.grid(row=4, column=0, padx=20, pady=10)
        self.sidebar_button_4 = ctk.CTkButton(self.sidebar_frame, text="Quit",command=self.stops)
        self.sidebar_button_4.grid(row=5, column=0, padx=20, pady=10)
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                    command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 10))
        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=9, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                            command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20))

        # create main entry and button
        self.entry = ctk.CTkEntry(self.root, placeholder_text="CTkEntry")
        self.entry.grid(row=1, column=1, padx=(20, 10), pady=(10, 10), sticky="nsew")

        # MAIN TABS
        self.tabview = ctk.CTkTabview(self.root, width=900)
        self.tabview.grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky="nsew")
        tab1 = self.tabview.add("Session")
        tab2 = self.tabview.add("Recording")
        tab3 = self.tabview.add("Data")
        tab4 = self.tabview.add("Analysis")
        tab5 = self.tabview.add("Settings") 
        tab1.grid_columnconfigure(2, weight=1) 
        tab2.grid_columnconfigure(1, weight=1)

        #TAB1 - Session
        self.session_id_label = ctk.CTkLabel(tab1, text="Session ID:")
        self.session_id_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.session_id_entry = ctk.CTkEntry(tab1, placeholder_text=self.session_id)
        self.session_id_entry.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.speakers_label = ctk.CTkLabel(tab1, text="Speakers:")
        self.speakers_label.grid(row=1, column=0, padx=20, pady=(20, 10))   
        self.speakers_entry = ctk.CTkEntry(tab1, placeholder_text=self.speakers)
        self.speakers_entry.grid(row=1, column=1, padx=20, pady=(20, 10))

        self.microphones_label = ctk.CTkLabel(tab1, text="Microphones:")
        self.microphones_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.microphones_entry = ctk.CTkEntry(tab1, placeholder_text=self.microphones)
        self.microphones_entry.grid(row=2, column=1, padx=20, pady=(20, 10))

        self.input_channels_label = ctk.CTkLabel(tab1, text="Input Channels:")
        self.input_channels_label.grid(row=3, column=0, padx=20, pady=(20, 10))
        self.input_channels_entry = ctk.CTkEntry(tab1, placeholder_text=self.inchan)
        self.input_channels_entry.grid(row=3, column=1, padx=20, pady=(20, 10))

        self.output_channels_label = ctk.CTkLabel(tab1, text="Output Channels:")
        self.output_channels_label.grid(row=4, column=0, padx=20, pady=(20, 10))
        self.output_channels_entry = ctk.CTkEntry(tab1, placeholder_text=self.outchan)
        self.output_channels_entry.grid(row=4, column=1, padx=20, pady=(20, 10))

        self.loopback_label = ctk.CTkLabel(tab1, text="Loopback:")
        self.loopback_label.grid(row=5, column=0, padx=20, pady=(20, 10))
        self.loopback_entry = ctk.CTkEntry(tab1, placeholder_text=self.loopback)
        self.loopback_entry.grid(row=5, column=1, padx=20, pady=(20, 10))

        self.sweep_file_label = ctk.CTkButton(tab1, text="Sweep File",command=self.open_sweep_file)
        self.sweep_file_label.grid(row=6, column=0, padx=20, pady=(20, 10)) 
        self.sweep_file_entry = ctk.CTkEntry(tab1, placeholder_text=self.sweep_file)
        self.sweep_file_entry.grid(row=6, column=1, padx=20, pady=(20, 10))

        self.sweep_generate_label = ctk.CTkButton(tab1, text="Generate Sweep",command=self.generate_sweep)
        self.sweep_generate_label.grid(row=7, column=0, padx=20, pady=(20, 10)) 

        self.recording_path_label = ctk.CTkButton(tab1, text="Recording Path",command=self.browse_recording_path) 
        self.recording_path_label.grid(row=8, column=0, padx=20, pady=(20, 10))
        self.recording_path_entry = ctk.CTkEntry(tab1, placeholder_text=self.recording_path)    
        self.recording_path_entry.grid(row=8, column=1, padx=20, pady=(20, 10))

        # Plano del lugar?
        self.map = ctk.CTkFrame(tab1, width=500, corner_radius=0)
        self.map.grid(row=0, column=2, rowspan=8, sticky="nsew")

        #TAB2 - Recording
        self.label_speaker = ctk.CTkLabel(tab2, text="SPEAKER")
        self.label_speaker.grid(row=0, column=0, padx=20, pady=0, sticky="w")

        self.label_microphone = ctk.CTkLabel(tab2, text="MICROPHONE")
        self.label_microphone.grid(row=0, column=1, padx=20, pady=0, sticky="w")

        self.label_direction = ctk.CTkLabel(tab2, text="DIRECTION")
        self.label_direction.grid(row=0, column=2, padx=20, pady=0, sticky="w")

        self.label_take = ctk.CTkLabel(tab2, text="TAKE")
        self.label_take.grid(row=0, column=3, padx=20, pady=0, sticky="w")

        self.speaker_box = ctk.CTkComboBox(master=tab2, values=[" "], variable=self.current_speaker)
        self.speaker_box.grid(row=1, column=0, padx=20, pady=0, sticky="w")

        self.microphone_box = ctk.CTkComboBox(master=tab2, values=[" "], variable=self.current_microphone)
        self.microphone_box.grid(row=1, column=1, padx=20, pady=0, sticky="w")

        self.direction_box = ctk.CTkComboBox(master=tab2, values=["1", "2", "3", "4", "5", "6"], variable=self.current_direction)    
        self.direction_box.grid(row=1, column=2, padx=20, pady=0, sticky="w")

        self.take_box = ctk.CTkComboBox(master=tab2, values=["1", "2", "3", "4", "5", "6"], variable=self.current_take)    
        self.take_box.grid(row=1, column=3, padx=20, pady=0, sticky="w")

        self.start_recording_button = ctk.CTkButton(tab2, text="Start Recording", command=self.start_recording)
        self.start_recording_button.grid(row=0, column=4, rowspan=2, padx=20, pady=20, sticky="e")

        #TAB3 - Data Table
        self.data_table = CTkTable(master=tab3, row=1, column=5, checkbox=True, 
                                   values=[["file", "speaker", "mic", "dir", "take"]], corner_radius=10)
        self.data_table.grid(row=1,column=0, padx=20, pady=20)
        send_button = ctk.CTkButton(master=tab3,text="Load",command=self.load_irs)
        send_button.grid(row=0, column=0, sticky="w", padx=20, pady=20)


        #TAB4 - Analysis

        #TAB5 - Settings

    def open_input_dialog_event(self):
        dialog = ctk.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def generate_sweep(self):
        if self.root.toplevel_window is None or not self.root.toplevel_window.winfo_exists():
            self.root.toplevel_window = GenerateWindow(self.root)  # create window if its None or destroyed
        else:
            self.root.toplevel_window.focus()  # if window exists focus it

    def browse_recording_path(self):
        recording_path = ctk.filedialog.askdirectory()
        self.recording_path_entry.delete(0, ctk.END)
        self.recording_path_entry.insert(ctk.END, recording_path)    

    def open_sweep_file(self):
        #filetypes = (('wav files', '*.wav'),('npy files', '*.npy'))
        filetypes = (('sweep files', 'sweep*.wav'),('wav files', '*.wav'),('npy files', '*.npy'))
        filename = ctk.filedialog.askopenfilename(title='Open a file',initialdir='./',filetypes=filetypes)
        self.sweep_file_entry.delete(0, ctk.END)    
        self.sweep_file_entry.insert(ctk.END, filename.split(".")[-2])

    def load_recording_session(self):
        print("sidebar_button click")
        self.browse_recording_path()
        #self.list_files()
        self.tick()

    def void_recording_session(self):
        self.recording_session = None
        self.session_id = ""
        self.speakers = []
        self.microphones = []
        self.recording_session = None
        self.current_speaker = None
        self.current_microphone = None   
        self.current_direction = None
        self.current_take = None
        self.pars = {}
        self.loaded_files = {}
        self.files = [] # list of files in recording_path
        #speaker_pos = self.speaker_pos_entry.get()
        #microphone_pos = self.microphone_pos_entry.get()
        self.inchan = []
        self.outchan = []
        self.loopback = None
        self.sampling_rate = fs
        self.rtype = ""
        self.recording_path = None
        self.sweep_file = None

    def clean_recording_session(self):
        self.void_recording_session    
        self.tick()

    def create_recording_session(self):
        # check if sesion already exists
        self.get_session_entries()
        self.entries_to_pars()
        # Create an instance of RecordingSession
        self.recording_session = RecordingSession(
            session_id=self.session_id,
            speakers=self.pars['speakers'],
            microphones=self.pars['microphones'],
            #speaker_pos=speaker_pos,
            #microphone_pos=microphone_pos,
            inchan=self.pars['inchan'],
            outchan=self.pars['outchan'],
            loopback=self.pars['loopback'],
            sampling_rate=self.pars['sampling_rate'],
            rtype=self.rtype,
            recordingpath=self.recording_path,
            sweepfile=self.sweep_file
        )
        self.list_files()
        self.tick()

    def get_session_entries(self):
        self.session_id = self.session_id_entry.get()
        self.speakers = self.speakers_entry.get()
        self.microphones = self.microphones_entry.get()
        #speaker_pos = self.speaker_pos_entry.get()
        #microphone_pos = self.microphone_pos_entry.get()
        self.inchan = self.input_channels_entry.get()
        self.outchan = self.output_channels_entry.get()
        self.loopback = self.loopback_entry.get()
        #self.sampling_rate = self.sampling_rate_entry.get()
        #self.rtype = self.rtype_entry.get()
        self.recording_path = self.recording_path_entry.get()
        self.sweep_file = self.sweep_file_entry.get()

    def entries_to_pars(self):
        # Convert some values to their appropriate types
        self.pars['speakers'] = ' '.join(self.speakers.split(',')).split()
        self.pars['microphones'] = ' '.join(self.microphones.split(',')).split()
        self.pars['inchan'] = list(map(int, ' '.join(self.inchan.split(',')).split()))
        self.pars['outchan'] = list(map(int, ' '.join(self.outchan.split(',')).split()))
        self.pars['loopback'] = int(self.loopback) if self.loopback != '' else None
        self.pars['sampling_rate'] = int(self.sampling_rate)

    def audio_init(self,device=None,fs=48000):
        # Inicia el Audio, chequear la configuracion el numero de device
        # Normalmente device = [input, output] donde el numero es el
        # device que devuelve el comando query_devices de sounddevice
        print("Iniciando Audio")
        devices = sd.query_devices() # por si hay dudas de cual es el dispositivo descomentar
        print(devices)
        if device is not None:
            sd.default.device = device
        input_device = sd.default.device[0]
        output_device = sd.default.device[1]
        output_name = devices[sd.default.device[1]]['name']
        input_name = devices[sd.default.device[0]]['name']
        print("Usando salida de audio: " + output_name)
        sd.default.samplerate = fs
        self.sampling_rate = fs
        self.max_chanin = devices[input_device]['max_input_channels']
        self.max_chanout = devices[output_device]['max_output_channels']

    def start_recording(self):
        print("start recording")
        self.current_speaker = self.speaker_box.get()
        self.current_microphone = self.microphone_box.get()
        self.current_direction = self.direction_box.get()
        self.current_take = self.take_box.get()
        print(f"Parlante {self.current_speaker}, Microfono {self.current_microphone}, Direccion {self.current_direction}, Toma {self.current_take}")    
        #self.recording_session.start_recording()
        self.recording_session.record_ir(
            self.current_speaker,
            self.current_microphone,
            self.current_direction,
            self.current_take
        )
        self.add_file()

    def list_files(self):
        print("load files")
        for n,rec in enumerate(self.recording_session.recordings):
            fname = rec['filename']
            self.data_table.add_row([[fname],rec['speaker'],rec['microphone'],rec['direction'],rec['take']])
            self.files.append(fname)

    def add_file(self):
        print("add file")
        fname = self.recording_session.recordings[-1]['filename']
        self.data_table.add_row([[fname],self.current_speaker,self.current_microphone,self.current_direction,self.current_take])
        self.files.append(fname)

    def remove_file(self):
        for n in range(len(self.files),1,-1):
            self.data_table.delete_row(n)
        self.files = []
        pass

    def load_irs(self):
        selected_files = self.data_table.get_checked()
        print("Selected files:", selected_files)

    def update_window(self):
        print("Update")
        self.get_session_entries()
        print(self.session_id)
        self.speaker_box.configure(values=self.pars['speakers'])
        self.microphone_box.configure(values=self.pars['microphones'])
        self.sidebar_label_1.configure(text=self.session_id)
        self.session_id_entry.delete(0, ctk.END)
        self.session_id_entry.insert(ctk.END,self.session_id)
        self.speakers_entry.delete(0, ctk.END)
        self.speakers_entry.insert(ctk.END,self.speakers)
        self.microphones_entry.delete(0, ctk.END)   
        self.microphones_entry.insert(ctk.END,self.microphones)
        # self.speaker_pos_entry.delete(0, ctk.END)
        # self.speaker_pos_entry.insert(ctk.END,speaker_pos)
        # self.microphone_pos_entry.delete(0, ctk.END)
        # self.microphone_pos_entry.insert(ctk.END,microphone_pos)  
        self.input_channels_entry.delete(0, ctk.END)
        self.input_channels_entry.insert(ctk.END,self.inchan)
        self.output_channels_entry.delete(0, ctk.END)
        self.output_channels_entry.insert(ctk.END,self.outchan)
        self.loopback_entry.delete(0, ctk.END)
        self.loopback_entry.insert(ctk.END,self.loopback) 
        

    def tick(self):
        self.root.update()
        self.root.update_idletasks()
        self.update_window()


    def stops(self):
        print("Stopping")
        self.save_and_close = True    
        #self.root.destroy()