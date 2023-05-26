import tkinter
import tkinter.messagebox
import customtkinter as ctk
from datetime import date, datetime
from yaml import safe_load
import sounddevice as sd
from session import RecordingSession
# las variables de la interfaz son siempre string y las de la clase RecordingSession 
# son del tipo que corresponde, con lo cual hay que convertir una en otra al guardar o cargar

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("dark-blue")  
fs = 48000 # default despues poner en menu

class App():
    def __init__(self):
        self.root = ctk.CTk()
        self.save_and_close = False
        # configure window
        self.root.title("ACOUSTIC FIELD")
        self.root.geometry(f"{1200}x{600}")
        self.root.minsize(600, 400)
        #self.iconbitmap("src/acousticfield/icon.ico")
        #self.protocol("WM_DELETE_WINDOW", self.close_event)
    
        # initialization
        self.void_recording_session()
        self.audio_init(fs=fs)
        self.recording_session = None
        # configure grid layout (4x4)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
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

        # create main tabview
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

        # Plano del lugar?
        self.map = ctk.CTkFrame(tab1, width=500, corner_radius=0)
        self.map.grid(row=0, column=2, rowspan=6, sticky="nsew")

        #TAB2 - Data
        self.label_tab_2 = ctk.CTkLabel(tab2, text="CTkLabel on Tab 2")
        self.label_tab_2.grid(row=0, column=0, padx=20, pady=20)

        #TAB3 - Analysis

        #TAB4 - Settings

    def open_input_dialog_event(self):
        dialog = ctk.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def browse_recording_path(self):
        recording_path = ctk.filedialog.askdirectory()
        self.recording_path_entry.delete(0, ctk.END)
        self.recording_path_entry.insert(ctk.END, recording_path)    

    def load_recording_session(self):
        print("sidebar_button click")
        self.browse_recording_path()
        self.tick()

    def void_recording_session(self):
        self.session_id = ""
        self.speakers = []
        self.microphones = []
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
        #self.recording_path = self.recording_path_entry.get()
        #self.sweep_file = self.sweep_file_entry.get()

        # Convert some values to their appropriate types
        speakers = self.speakers.split(',')
        microphones = self.microphones.split(',')
        inchan = list(map(int, self.inchan.split(',')))
        outchan = list(map(int, self.outchan.split(',')))
        loopback = int(self.loopback)
        sampling_rate = int(self.sampling_rate)

        # Create an instance of RecordingSession
        self.recording_session = RecordingSession(
            session_id=self.session_id,
            speakers=speakers,
            microphones=microphones,
            #speaker_pos=speaker_pos,
            #microphone_pos=microphone_pos,
            inchan=inchan,
            outchan=outchan,
            loopback=loopback,
            sampling_rate=sampling_rate,
            rtype=self.rtype,
            recordingpath=self.recording_path,
            sweepfile=self.sweep_file
        )
        self.tick()
        print(vars(self.recording_session))

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

    def update_window(self):
        print("Update")
        self.session_id = self.session_id_entry.get()
        self.speakers = self.speakers_entry.get()
        self.microphones = self.microphones_entry.get()
        #speaker_pos = self.speaker_pos_entry.get()
        #microphone_pos = self.microphone_pos_entry.get()
        self.inchan = self.input_channels_entry.get()
        self.outchan = self.output_channels_entry.get()
        self.loopback = self.loopback_entry.get()
        self.sidebar_label_1.configure(text=self.session_id)
        self.session_id_entry.configure(placeholder_text=self.session_id)
        self.speakers_entry.configure(placeholder_text=self.speakers)
        self.microphones_entry.configure(placeholder_text=self.microphones)
        self.input_channels_entry.configure(placeholder_text=self.inchan)
        self.output_channels_entry.configure(placeholder_text=self.outchan)
        self.loopback_entry.configure(placeholder_text=self.loopback)
        self.newdata = False

    def tick(self):
        self.update_window()
        self.root.update()
        self.root.update_idletasks()


    def stops(self):
        print("Stopping")
        self.save_and_close = True    

if __name__ == "__main__":
    app = App()
    #inicia audio
    # Crea Ventanas
    #app.root.mainloop()
    while app.save_and_close == False:
        app.root.update()