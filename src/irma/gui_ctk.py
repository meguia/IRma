# IRMA - Impulse Response Measurement and Analysis
# 2020-2025 LAPSo - Laboratorio de Acústica y Percepción Sonora - Universidad Nacional de Quilmes
# Licensed under MIT License - see LICENSE file in main directory
# this file has blocks marked with #region and #endregion for better navigation
# toggle the display of these blocks use the commands Ctrl+K and Ctrl+L in VSCode

#region IMPORTS AND SETTINGS
import customtkinter as ctk
import os
import csv
import sounddevice as sd
import pathlib
import threading
import queue
import traceback
from .generate import sweep
from .process import ir_list_to_multichannel,make_filterbank,load_filterbank
from .room import paracoustic
from .display import ir_plot, pars_compared_axes,irstat_plot,parsdecay_plot,echo_display, spectrum_plot
from .session import RecordingSession
from .utils.ctkutils import *
from .utils.audioutils import *

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("dark-blue")  
#endregion

#region GENERATE SWEEP
class GenerateSweep(ctk.CTkToplevel):
    def __init__(self, main_frame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x500")
        self.parent = main_frame
        self.title("Generate Sweep")
        self.sampling_rate = ctkstring_to_value(self.parent.sampling_rate, type='int')
        self.label = ctk.CTkLabel(self, text=f"Generate Log Sweep\nSampling Rate: {self.sampling_rate} Hz")
        self.label.grid(row=0,column=0,columnspan=2, padx=20, pady=20)
        
        self.label_fmin = ctk.CTkLabel(self, text="fmin")
        self.label_fmin.grid(row=1,column=0,padx=20, pady=10)
        self.sweep_fmin_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=20))
        self.sweep_fmin_entry.grid(row=1,column=1,padx=20, pady=10)

        self.label_fmax = ctk.CTkLabel(self, text="fmax")
        self.label_fmax.grid(row=2,column=0,padx=20, pady=10)
        self.sweep_fmax_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=20000))
        self.sweep_fmax_entry.grid(row=2,column=1,padx=20, pady=10)

        self.label_post = ctk.CTkLabel(self, text="duration")
        self.label_post.grid(row=3,column=0,padx=20, pady=10)
        self.sweep_dur_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=10.0)) # en segundos
        self.sweep_dur_entry.grid(row=3,column=1,padx=20, pady=10) 

        self.label_post = ctk.CTkLabel(self, text="post")
        self.label_post.grid(row=4,column=0,padx=20, pady=10)   
        self.sweep_post_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=1.0)) # en segundos
        self.sweep_post_entry.grid(row=4,column=1,padx=20, pady=10)

        self.label_rep = ctk.CTkLabel(self, text="repetitions")
        self.label_rep.grid(row=5,column=0,padx=20, pady=10)
        self.sweep_rep_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=1)) 
        self.sweep_rep_entry.grid(row=5,column=1,padx=20, pady=10)

        self.generate_button = ctk.CTkButton(self, text="Generate", command=self.generate)
        self.generate_button.grid(row=6,column=0,columnspan=2,padx=20, pady=20)

    def generate(self):
        self.sweep_fmin = self.parent.validate_entry(self.sweep_fmin_entry, type='int')
        self.sweep_fmax = self.parent.validate_entry(self.sweep_fmax_entry, type='int')
        self.sweep_dur = self.parent.validate_entry(self.sweep_dur_entry, type='float')
        self.sweep_post = self.parent.validate_entry(self.sweep_post_entry, type='float')
        #self.sweep_rep = self.parent.validate_entry(self.sweep_rep_entry, type='int')
        self.sweep_rep = 1 # not repetitions for session sweeps (to be added later)

        srkhz = self.sampling_rate//1000
        maxrange = self.sweep_fmax//1000
        self.sweepfile = f"sweep_x{self.sweep_rep}_{srkhz}k_{int(self.sweep_dur)}s_{self.sweep_fmin}_{maxrange}k"
        print("generating sweep " + self.sweepfile)
        sweep(T=self.sweep_dur,fs=self.sampling_rate,f1=self.sweep_fmin,f2=self.sweep_fmax,Nrep=self.sweep_rep,
        filename=self.sweepfile,post=self.sweep_post)
        self.parent.sweep_file = self.sweepfile
        self.parent.rewrite_entry(self.parent.sweep_file_entry,[self.sweepfile])
        self.parent.rewrite_textbox(self.parent.status,f"Sweep generated in {self.sweepfile}.wav")
        self.destroy()
#endregion  

#region GENERATE FILTERBANK
class GenerateFilterBank(ctk.CTkToplevel):
    def __init__(self, main_frame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x500")
        self.title("Generate Filter Bank")
        self.label = ctk.CTkLabel(self, text="Generate Filter Bank")
        self.label.grid(row=0,column=0,columnspan=2,padx=20, pady=20)
        self.parent = main_frame
        self.sampling_rate = ctkstring_to_value(self.parent.sampling_rate, type='int')
        self.label_fmin = ctk.CTkLabel(self, text="fmin")
        self.label_fmin.grid(row=1,column=0,padx=20, pady=20)
        self.fmin_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=62.5))
        self.fmin_entry.grid(row=1,column=1,padx=20, pady=20)

        self.label_noct = ctk.CTkLabel(self, text="Number of octaves")
        self.label_noct.grid(row=2,column=0,padx=20, pady=20)
        self.noct_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=8))
        self.noct_entry.grid(row=2,column=1,padx=20, pady=20)

        self.label_bwoct = ctk.CTkLabel(self, text="Bands per octave")
        self.label_bwoct.grid(row=3,column=0,padx=20, pady=20)
        self.bwoct_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=1))
        self.bwoct_entry.grid(row=3,column=1,padx=20, pady=20)

        self.label_fs = ctk.CTkLabel(self, text="Sampling rate")
        self.label_fs.grid(row=4,column=0,padx=20, pady=20)
        self.fs_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=self.sampling_rate)) # en segundos
        self.fs_entry.grid(row=4,column=1,padx=20, pady=20) 

        self.label_order = ctk.CTkLabel(self, text="Order")
        self.label_order.grid(row=5,column=0,padx=20, pady=20)   
        self.order_entry = ctk.CTkEntry(self, textvariable=ctk.StringVar(value=5)) # en segundos
        self.order_entry.grid(row=5,column=1,padx=20, pady=20)

        self.generate_button = ctk.CTkButton(self, text="Generate", command=self.generate)
        self.generate_button.grid(row=6,column=0,padx=20, pady=20)

    def generate(self):
        self.fmin = self.parent.validate_entry(self.fmin_entry, type='float')
        self.noct = self.parent.validate_entry(self.noct_entry, type='int')
        self.bwoct = self.parent.validate_entry(self.bwoct_entry, type='int')
        self.fs = self.parent.validate_entry(self.fs_entry, type='int')
        self.order = self.parent.validate_entry(self.order_entry, type='int')
        #self.name = self.name_entry.get()
        #srkhz = self.sampling_rate//1000
        #self.fbankfile = f"fbank_{srkhz}k_{self.noct}_{self.bwoct}"
        self.fbankfile = "fbank"
        print("generating filter bank " + self.fbankfile)
        make_filterbank(fmin=self.fmin,noct=self.noct,bwoct=self.bwoct,fs=self.sampling_rate,\
                        order=self.order,N=10000,bankname=self.fbankfile)
        self.parent.parameter_table_headers, _ = load_filterbank(self.fbankfile)
        self.parent.parameter_table_headers.insert(0,'Band')
        self.parent.rewrite_textbox(self.parent.status,f"Filter Bank generated in {self.fbankfile}.npz")
        #remake table with new headers
        self.parent.parameter_table.destroy_table()
        self.parent.parameter_table.values = [self.parent.parameter_table_headers]
        self.parent.parameter_table.columns=len(self.parent.parameter_table_headers)
        self.parent.parameter_table.draw_table()
        self.parent.parameter_table.edit_column(column=0,values=self.parent.parameter_table_keys)
        self.destroy()
#endregion        

#region MAIN WINDOW
class IRMA_ctk():
    def __init__(self):
        self.root = ctk.CTk()
        self.save_and_close = False
        # configure window
        self.root.title("IRMA Impulse Response Measurement and Analysis")
        self.root.geometry(f"{1200}x{700}")
        self.root.minsize(600, 400)
        #self.root.iconbitmap("src/irma/icon.ico")
        self.root.protocol("WM_DELETE_WINDOW", self.stops)
        # initialization fonts
        self.fbig = ctk.CTkFont(family="Roboto", size=32)
        self.fnorm = ctk.CTkFont(family="Roboto", size=18)
        self.fsmall = ctk.CTkFont(family="Roboto", size=14)
        # settings
        self.inputs, self.outputs = list_devices()
        self.void_recording_session()
        # configure grid layout (4x4)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.toplevel_window = None
        self.create_static_widgets()
        self.create_settings_widgets()
        self.create_widgets()
        # workers threading
        self._worker_queue = queue.Queue()
        self._worker_thread = None
        self._test_input_queue = queue.Queue()
        self._test_input_stop = threading.Event()
        self._test_input_thread = None
        self._test_output_queue = queue.Queue()
        self._test_output_stop = threading.Event()
        self._test_output_thread = None
        self._busy = False
        self._closing = False
        self._after_ids = set()

#endregion

#region STATIC WIDGETS
    def create_static_widgets(self):
        self.sidebar_frame = ctk.CTkFrame(self.root, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)
        # SIDEBAR
        self.sidebar_label_1 = ctk.CTkLabel(self.sidebar_frame, text="Session", font=self.fsmall)
        self.sidebar_label_1.grid(row=0, column=0, padx=20, pady=(20,0))
        self.button_create = ctk.CTkButton(self.sidebar_frame, text="Create",font=self.fnorm,command=self.create_recording_session)
        self.button_create.grid(row=2, column=0, padx=20, pady=10)
        self.button_save = ctk.CTkButton(self.sidebar_frame, text="Save",font=self.fnorm,command=self.save_recording_session)
        self.button_save.grid(row=3, column=0, padx=20, pady=10)
        self.button_load = ctk.CTkButton(self.sidebar_frame, text="Load",font=self.fnorm,command=self.load_recording_session)
        self.button_load.grid(row=4, column=0, padx=20, pady=10)
        self.button_clean = ctk.CTkButton(self.sidebar_frame, text="Clean",font=self.fnorm,command=self.clean_recording_session)
        self.button_clean.grid(row=5, column=0, padx=20, pady=10)
        self.button_quit = ctk.CTkButton(self.sidebar_frame, text="Quit",font=self.fnorm,command=self.stops)
        self.button_quit.grid(row=6, column=0, padx=20, pady=10)
        self.separator = ctk.CTkLabel(self.sidebar_frame, text="", anchor="w")
        self.separator.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=8, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                    command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=9, column=0, padx=20, pady=(10, 10))
        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=10, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                            command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=11, column=0, padx=20, pady=(10, 20))
        # create status an message bar
        self.status = ctk.CTkTextbox(self.root,height=40, font=self.fnorm)
        self.status.grid(row=1, column=1, padx=(20, 10), pady=(10, 10), sticky="nsew")
        self.status.insert("0.0", "Welcome to IRMA! Please create a new session or load an existing one")
        # MAIN TABS
        self.tabview = ctk.CTkTabview(self.root, width=900)
        self.tabview.grid(row=0, column=1, padx=(20, 10), pady=(0, 0), sticky="nsew")
        self.tab_session = self.tabview.add(" SESSION ")
        self.tab_recording = self.tabview.add(" RECORDING ")
        self.tab_data = self.tabview.add(" DATA ")
        self.tab_stats = self.tabview.add(" IR ")
        self.tab_transfer = self.tabview.add(" TRANSFER ")
        self.tab_table = self.tabview.add(" TABLE ")
        self.tab_plot = self.tabview.add(" PLOT ")
        self.tab_decays = self.tabview.add(" DECAYS ")
        self.tab_settings = self.tabview.add(" SETTINGS")

        self.tab_session.grid_columnconfigure(2, weight=1)
        self.tab_recording.grid_columnconfigure(0, weight=1)
        self.tab_data.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_columnconfigure(0, weight=1)
        self.tab_transfer.grid_columnconfigure(0, weight=1)
        self.tab_table.grid_columnconfigure(0, weight=1)
        self.tab_table.grid_rowconfigure(2, weight=1)
        self.tab_plot.grid_columnconfigure(0, weight=1)
        self.tab_decays.grid_columnconfigure(0, weight=1)
        #TAB SESSION
        self.session_id_label = ctk.CTkLabel(self.tab_session, text="Session ID:")
        self.session_id_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.speakers_label = ctk.CTkLabel(self.tab_session, text="Speakers:")
        self.speakers_label.grid(row=1, column=0, padx=20, pady=(20, 10))           
        self.microphones_label = ctk.CTkLabel(self.tab_session, text="Microphones:")
        self.microphones_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.input_channels_label = ctk.CTkLabel(self.tab_session, text="Input Channels:")
        self.input_channels_label.grid(row=3, column=0, padx=20, pady=(20, 10))
        self.output_channels_label = ctk.CTkLabel(self.tab_session, text="Output Channels:")
        self.loopback_label = ctk.CTkLabel(self.tab_session, text="Loopback:")
        self.loopback_label.grid(row=5, column=0, padx=20, pady=(20, 10))

        self.output_channels_label.grid(row=4, column=0, padx=20, pady=(20, 10))
        self.sweep_file_button = ctk.CTkButton(self.tab_session, text="Sweep File",command=self.open_sweep_file)
        self.sweep_file_button.grid(row=6, column=0, padx=20, pady=(20, 10)) 
        self.sweep_file_entry = ctk.CTkEntry(self.tab_session, placeholder_text=self.sweep_file)
        self.sweep_file_entry.grid(row=6, column=1, padx=20, pady=(20, 10))
        self.sweep_generate_label = ctk.CTkButton(self.tab_session, text="Generate Sweep",command=self.generate_sweep)
        self.sweep_generate_label.grid(row=7, column=0, padx=20, pady=(20, 10)) 
        self.recording_path_button = ctk.CTkButton(self.tab_session, text="Recording Path",command=self.browse_recording_path) 
        self.recording_path_button.grid(row=8, column=0, padx=20, pady=(20, 10))
        self.recording_path_entry = ctk.CTkEntry(self.tab_session, placeholder_text=self.recording_path)    
        self.recording_path_entry.grid(row=8, column=1, padx=20, pady=(20, 10))
        # Plano del lugar?
        self.map = ctk.CTkFrame(self.tab_session, width=500, corner_radius=0)
        self.map.grid(row=0, column=2, rowspan=9, sticky="nsew")
         #TAB2 - Recording
        self.label_speaker = ctk.CTkLabel(self.tab_recording, text="SPEAKER")
        self.label_speaker.grid(row=0, column=0, padx=10, pady=0, sticky="w")
        self.label_microphone = ctk.CTkLabel(self.tab_recording, text="MICROPHONE")
        self.label_microphone.grid(row=0, column=2, padx=10, pady=0, sticky="w")
        self.label_direction = ctk.CTkLabel(self.tab_recording, text="DIRECTION")
        self.label_direction.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.label_take = ctk.CTkLabel(self.tab_recording, text="TAKE")
        self.label_take.grid(row=0, column=6, padx=10, pady=0, sticky="w")
        self.start_recording_button = ctk.CTkButton(self.tab_recording, text="Start Recording", command=self.start_recording)
        self.start_recording_button.grid(row=0, column=8, padx=10, pady=0, sticky="w")
        self.label_comment = ctk.CTkLabel(self.tab_recording, text="comment")
        self.label_comment.grid(row=1, column=0, padx=10, pady=0, sticky="w")


    def create_settings_widgets(self):
        self.label_select_input = ctk.CTkLabel(self.tab_settings, text="Audio Input")
        self.label_select_input.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        self.label_select_output = ctk.CTkLabel(self.tab_settings, text="Audio Output")
        self.label_select_output.grid(row=1, column=0, padx=10, pady=20, sticky="w")
        self.label_sampling_rate = ctk.CTkLabel(self.tab_settings, text="Sampling Rate")
        self.label_sampling_rate.grid(row=2, column=0, padx=10, pady=20, sticky="w")

        self.select_input_box = ctk.CTkOptionMenu(master=self.tab_settings, values=self.inputs, variable=self.input_device)
        self.select_input_box.grid(row=0, column=1, padx=10, pady=20, sticky="w")
        self.select_output_box = ctk.CTkOptionMenu(master=self.tab_settings, values=self.outputs, variable=self.output_device)
        self.select_output_box.grid(row=1, column=1, padx=10, pady=20, sticky="w")
        self.sampling_rate_box = ctk.CTkOptionMenu(master=self.tab_settings, values=["44100", "48000","96000"], variable=self.sampling_rate)
        self.sampling_rate_box.grid(row=2, column=1, padx=10, pady=20, sticky="w")

        self.test_input_button = ctk.CTkButton(self.tab_settings, text="Test Input", command=self.test_input)
        self.test_input_button.grid(row=0, column=2, padx=10, pady=20, sticky="w")
        self.test_output_button = ctk.CTkButton(self.tab_settings, text="Test Output", command=self.test_output)
        self.test_output_button.grid(row=1, column=2, padx=10, pady=20, sticky="w")
        self.save_settings_button = ctk.CTkButton(self.tab_settings, text="Save Settings", command=self.save_settings)
        self.save_settings_button.grid(row=3, column=0, columnspan=2, padx=0, pady=20, sticky="e")

        self.test_input_bar = ctk.CTkProgressBar(self.tab_settings, width=200, orientation='horizontal',mode='determinate')
        self.test_input_bar.grid(row=0, column=3, padx=10, pady=20, sticky="w")
        self.test_input_bar.set(0)    
#endregion

#region WIDGETS
    def create_widgets(self):
        # sidebar frame with widgets
        self.sidebar_label_2 = ctk.CTkLabel(self.sidebar_frame, text=self.session_id.get(), text_color="#f5d2d2", font=self.fbig)
        self.sidebar_label_2.grid(row=1, column=0, padx=20, pady=(20, 10))
        #TAB1 - Session
        self.session_id_entry = ctk.CTkEntry(self.tab_session, textvariable=self.session_id)
        self.session_id_entry.grid(row=0, column=1, padx=20, pady=(20, 10))
        self.speakers_entry = ctk.CTkEntry(self.tab_session, textvariable=self.speakers)
        self.speakers_entry.grid(row=1, column=1, padx=20, pady=(20, 10))
        self.microphones_entry = ctk.CTkEntry(self.tab_session, textvariable=self.microphones)
        self.microphones_entry.grid(row=2, column=1, padx=20, pady=(20, 10))       
        self.input_channels_entry = ctk.CTkEntry(self.tab_session, textvariable=self.inchan)
        self.input_channels_entry.grid(row=3, column=1, padx=20, pady=(20, 10))        
        self.output_channels_entry = ctk.CTkEntry(self.tab_session, textvariable=self.outchan)
        self.output_channels_entry.grid(row=4, column=1, padx=20, pady=(20, 10))        
        self.loopback_entry = ctk.CTkEntry(self.tab_session, textvariable=self.loopback)
        self.loopback_entry.grid(row=5, column=1, padx=20, pady=(20, 10))

        #TAB2 - Recording
        self.speaker_box = ctk.CTkComboBox(master=self.tab_recording, values=[" "], variable=self.current_speaker)
        self.speaker_box.grid(row=0, column=1, padx=10, pady=0, sticky="w")
        self.microphone_box = ctk.CTkComboBox(master=self.tab_recording, values=[" "], variable=self.current_microphone)
        self.microphone_box.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.direction_box = ctk.CTkComboBox(master=self.tab_recording, width=30,values=["1", "2", "3", "4", "5", "6"], variable=self.current_direction)    
        self.direction_box.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.take_box = ctk.CTkComboBox(master=self.tab_recording, width=30,values=["1", "2", "3", "4", "5", "6"], variable=self.current_take)    
        self.take_box.grid(row=0, column=7, padx=10, pady=0, sticky="w")

        self.comment_entry = ctk.CTkEntry(master=self.tab_recording, textvariable=self.comment)
        self.comment_entry.grid(row=1, column=1, columnspan=8, padx=10, pady=10, sticky="nsew")        
        #plot ir
        self.plot_ir_frame = ctk.CTkFrame(self.tab_recording, corner_radius=25)
        self.plot_ir_frame.grid(row=2, column=0, columnspan=9, sticky="nsew")
        self.matplotlib_ir_frame = PlotFrame(self.plot_ir_frame, corner_radius=25)
        self.matplotlib_ir_frame.pack(fill=ctk.BOTH, expand=True)
        self.matplotlib_ir_axes = self.matplotlib_ir_frame.axes
        
        #TAB3 - Data Table
        self.data_table = CTkTable(master=self.tab_data, row=1, column=6, checkbox=True, values=[["file", "speaker", "mic", "dir", "take","nchan"]], 
                                   corner_radius=10, header_color=True,column1st_color=True)
        self.data_table.grid(row=1,column=0, padx=20, pady=20)
        self.load_button = ctk.CTkButton(master=self.tab_data,text="Load",command=self.load_irs)
        self.load_button.grid(row=0, column=0, sticky="w", padx=20, pady=20)

        #self.tab_stats - IR Stats
        self.label_tmax = ctk.CTkLabel(self.tab_stats, text="Time Max")
        self.label_tmax.grid(row=0, column=0, padx=10, pady=0, sticky="e")
        self.tmax_entry = ctk.CTkEntry(master=self.tab_stats, width=50,textvariable=self.tmax)
        self.tmax_entry.grid(row=0, column=1, padx=10, pady=0, sticky="e")
        self.label_file_s = ctk.CTkLabel(self.tab_stats, text="File")
        self.label_file_s.grid(row=0, column=2, padx=10, pady=0, sticky="w")
        self.select_file_box_s = ctk.CTkComboBox(master=self.tab_stats, values=[" "], width=180,variable=self.current_file,command=self.set_channel)
        self.select_file_box_s.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.label_channel_s = ctk.CTkLabel(self.tab_stats, text="Channel")
        self.label_channel_s.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.select_channel_box_s = ctk.CTkComboBox(master=self.tab_stats, values=['1'], width=30,variable=self.current_channel)
        self.select_channel_box_s.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.select_plot_stats_box = ctk.CTkComboBox(master=self.tab_stats, values=["IR Plot","IR Echo","IR Stats"], variable=self.current_plot_stats)
        self.select_plot_stats_box.grid(row=0, column=6, sticky="w", padx=10, pady=0)
        self.plot_stats_overlay = ctk.CTkSwitch(self.tab_stats, text="Over", onvalue="on", offvalue="off")
        self.plot_stats_overlay.grid(row=0, column=7, padx=10, pady=0, sticky="w")
        self.plot_stats_button = ctk.CTkButton(self.tab_stats, text="Plot", command=self.plot_stats)
        self.plot_stats_button.grid(row=0, column=8, padx=10, pady=0, sticky="e")
        self.plot_stats_frame = ctk.CTkFrame(self.tab_stats, corner_radius=25)
        self.plot_stats_frame.grid(row=1, column=0, columnspan=9, sticky="nsew")
        self.matplotlib_stats_frame = PlotFrame(self.plot_stats_frame, corner_radius=25)
        self.matplotlib_stats_frame.pack(fill=ctk.BOTH, expand=True)
        self.matplotlib_stats_axes = self.matplotlib_stats_frame.axes

        #self.tab_transfer - Transfer Function
        self.label_file_t = ctk.CTkLabel(self.tab_transfer, text="File")
        self.label_file_t.grid(row=0, column=2, padx=10, pady=0, sticky="w")
        self.select_file_box_t = ctk.CTkComboBox(master=self.tab_transfer, values=[" "], width=180,variable=self.current_file,command=self.set_channel)
        self.select_file_box_t.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.label_channel_t = ctk.CTkLabel(self.tab_transfer, text="Channel")
        self.label_channel_t.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.select_channel_box_t = ctk.CTkComboBox(master=self.tab_transfer, values=['1'], width=30,variable=self.current_channel)
        self.select_channel_box_t.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.plot_transfer_log = ctk.CTkSwitch(self.tab_transfer, text="Log f", variable=self.logscale, onvalue="on", offvalue="off")
        self.plot_transfer_log.grid(row=0, column=6, padx=10, pady=0, sticky="w")
        self.plot_transfer_overlay = ctk.CTkSwitch(self.tab_transfer, text="Over", onvalue="on", offvalue="off")
        self.plot_transfer_overlay.grid(row=0, column=7, padx=10, pady=0, sticky="w")
        self.plot_transfer_button = ctk.CTkButton(self.tab_transfer, text="Plot", command=self.plot_transfer)
        self.plot_transfer_button.grid(row=0, column=8, padx=10, pady=0, sticky="e")
        self.plot_transfer_frame = ctk.CTkFrame(self.tab_transfer, corner_radius=25)
        self.plot_transfer_frame.grid(row=1, column=0, columnspan=9, sticky="nsew")
        self.matplotlib_transfer_frame = PlotFrame(self.plot_transfer_frame, corner_radius=25)
        self.matplotlib_transfer_frame.pack(fill=ctk.BOTH, expand=True)
        self.matplotlib_transfer_axes = self.matplotlib_transfer_frame.axes


        #self.tab_table - Parameters Table
        self.parameter_table_keys = ['Band',self.rtmethod,'rvalue','EDT','C50','C80','TS','DRR','SNR']
        self.parameter_table = CTkTable(master=self.tab_table, row=len(self.parameter_table_keys), column=len(self.parameter_table_headers), 
                                        checkbox=False, values=[self.parameter_table_headers], corner_radius=10,header_color=True,column1st_color=True)
        self.parameter_table.grid(row=1,column=0, columnspan=8, padx=20, pady=20)
        self.parameter_table.edit_column(column=0,values=self.parameter_table_keys)
        self.comment_box = ctk.CTkTextbox(master=self.tab_table, height=10)
        self.comment_box.grid(row=2, column=0, columnspan=8, padx=10, pady=10, sticky="nsew")

        self.filterbank_button = ctk.CTkButton(master=self.tab_table,text="Filter Bank",command=self.generate_filterbank)
        self.filterbank_button.grid(row=0, column=0, sticky="w", padx=10, pady=20)
        self.label_method = ctk.CTkLabel(self.tab_table, text="Method")
        self.label_method.grid(row=0, column=1, padx=10, pady=0, sticky="w")
        self.select_method_box = ctk.CTkComboBox(master=self.tab_table, values=["RT20","RT15","RT30"], width=100,variable=self.rtmethod,command=self.set_method)
        self.select_method_box.grid(row=0, column=2, padx=10, pady=0, sticky="w")
        self.label_file = ctk.CTkLabel(self.tab_table, text="File")
        self.label_file.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.select_file_box = ctk.CTkComboBox(master=self.tab_table, values=[" "], width=180, variable=self.current_file,command=self.set_channel)
        self.select_file_box.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.label_channel = ctk.CTkLabel(self.tab_table, text="Channel")
        self.label_channel.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.select_channel_box = ctk.CTkComboBox(master=self.tab_table, values=['1'], width=30,variable=self.current_channel)
        self.select_channel_box.grid(row=0, column=6, padx=10, pady=0, sticky="w")
        self.table_button = ctk.CTkButton(master=self.tab_table,text="Display",command=self.display_params)
        self.table_button.grid(row=0, column=7, sticky="w", padx=10, pady=20)
        self.table_save_button = ctk.CTkButton(master=self.tab_table,text="Save",command=self.save_table)
        self.table_save_button.grid(row=3, column=7, sticky="w", padx=10, pady=20)

        #self.tab_plot - Parameters Plots
        self.parameter_plot_keys = [self.rtmethod,'EDT','C50','C80','TS','DRR','SNR']
        self.label_key = ctk.CTkLabel(self.tab_plot, text="Parameter")
        self.label_key.grid(row=0, column=1, padx=20, pady=0, sticky="w")
        self.select_key_box = ctk.CTkComboBox(master=self.tab_plot, values=self.parameter_plot_keys, variable=self.current_key)
        self.select_key_box.grid(row=0, column=2, padx=20, pady=0, sticky="w")

        self.label_file_p = ctk.CTkLabel(self.tab_plot, text="File")
        self.label_file_p.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.select_file_box_p = ctk.CTkComboBox(master=self.tab_plot, values=[" "], width=180, variable=self.plot_files,command=self.set_plot_channels)
        self.select_file_box_p.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.label_channel_p = ctk.CTkLabel(self.tab_plot, text="Channel")
        self.label_channel_p.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.select_channel_box_p = ctk.CTkComboBox(master=self.tab_plot, values=["1"], width=100,variable=self.plot_channels)
        self.select_channel_box_p.grid(row=0, column=6, padx=10, pady=0, sticky="w")
        self.analyze_button = ctk.CTkButton(self.tab_plot, text="Analyze", command=self.analyze)
        self.analyze_button.grid(row=0, column=7, padx=20, pady=20, sticky="e")

        self.plot_analysis_frame = ctk.CTkFrame(self.tab_plot, corner_radius=25)
        self.plot_analysis_frame.grid(row=2, column=0, columnspan=8, sticky="nsew")
        self.matplotlib_analysis_frame = PlotFrame(self.plot_analysis_frame)
        self.matplotlib_analysis_frame.pack(fill=ctk.BOTH, expand=True)
        self.matplotlib_analysis_axes = self.matplotlib_analysis_frame.axes

        #self.tab_decays - Decays Plots
        self.label_file_d = ctk.CTkLabel(self.tab_decays, text="File")
        self.label_file_d.grid(row=0, column=3, padx=10, pady=0, sticky="w")
        self.select_file_box_d = ctk.CTkComboBox(master=self.tab_decays, values=[" "], width=180, variable=self.current_file,command=self.set_channel)
        self.select_file_box_d.grid(row=0, column=4, padx=10, pady=0, sticky="w")
        self.label_channel_d = ctk.CTkLabel(self.tab_decays, text="Channel")
        self.label_channel_d.grid(row=0, column=5, padx=10, pady=0, sticky="w")
        self.select_channel_box_d = ctk.CTkComboBox(master=self.tab_decays, values=['1'], width=30,variable=self.current_channel)
        self.select_channel_box_d.grid(row=0, column=6, padx=10, pady=0, sticky="w")
        self.plot_decay_button = ctk.CTkButton(self.tab_decays, text="Plot Decays", command=self.plot_decays)
        self.plot_decay_button.grid(row=0, column=7, padx=20, pady=20, sticky="e")

        self.plot_decay_frame = ctk.CTkFrame(self.tab_decays, width=900, height=500, corner_radius=25)
        self.plot_decay_frame.grid(row=1, column=0, columnspan=8, sticky="nsew")
        self.image_decay_frame = ctk.CTkLabel(self.plot_decay_frame, image=None, text='')
        self.image_decay_frame.pack(fill=ctk.BOTH, expand=True)
#endregion

#region GEOMETRY AND SESSION BUTTONS
    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def generate_sweep(self):
        if self.root.toplevel_window is None or not self.root.toplevel_window.winfo_exists():
            self.root.toplevel_window = GenerateSweep(self)  # create window if its None or destroyed
        else:
            self.root.toplevel_window.focus()  # if window exists focus it

    def generate_filterbank(self):
        if self.root.toplevel_window is None or not self.root.toplevel_window.winfo_exists():
            self.root.toplevel_window = GenerateFilterBank(self)  # create window if its None or destroyed
        else:
            self.root.toplevel_window.focus()  # if window exists focus it   
        

    def browse_recording_path(self):
        recording_path = ctk.filedialog.askdirectory()
        self.recording_path_entry.delete(0, ctk.END)
        self.recording_path_entry.insert(ctk.END, recording_path)
        self.recording_path = recording_path    

    def open_sweep_file(self):
        filetypes = (('sweep files', 'sweep*.wav'),('wav files', '*.wav'),('npy files', '*.npy'))
        filename = ctk.filedialog.askopenfilename(title='Open a file',initialdir='./',filetypes=filetypes)
        self.sweep_file_entry.delete(0, ctk.END)    
        self.sweep_file_entry.insert(ctk.END, os.path.splitext(filename)[0])
        self.sweep_file = os.path.splitext(filename)[0]
#endregion

#region SAVE CLEAR AND LOAD SESSION

    def save_recording_session(self):
        #check if the recording session was created
        if self.recording_session is None:
            self.rewrite_textbox(self.status, "No session to save (create or load one first).")
            return
        #check if the recording session was saved
        #if self.recording_session.saved:
            #popup window warning
        #    return
        self.entries_to_pars()
        self.pars_to_session()
        session_id = (self.pars.get("session_id") or "").strip()
        if not session_id:
            self.rewrite_textbox(self.status, "Session ID is empty; cannot save.")
            return
        recording_path = (self.pars.get("recording_path") or "").strip()
        if not recording_path:
            self.rewrite_textbox(self.status, "Recording path is empty; cannot save.")
            return
        outpath = pathlib.Path(recording_path) / f"{session_id}.yaml"

        try:
            self.recording_session.save_metadata(outpath)
            msg = f"Session saved: {outpath}"
            print(msg)
            self.rewrite_textbox(self.status, msg)
        except Exception as e:
            print("Session save failed:", repr(e))
            traceback.print_exc()
            self.rewrite_textbox(self.status, f"Session save failed: {e!r}")
            #self.recording_session.saved = True
        
    
    def load_recording_session(self):
        filetypes = (('yaml files', '*.yaml'),('all files', '*.*'))
        filename = ctk.filedialog.askopenfilename(title='Open a file',initialdir='./',filetypes=filetypes)
        print(filename)
        
        if filename == "":
            return
        if self.recording_session is None:
            self.recording_session = RecordingSession(session_id="")
        self.rewrite_textbox(self.status,f"Opening Session saved in: {filename}")    
        s = self.recording_session.load_metadata(filename)
        self.recording_session = s
        self.sidebar_label_2.configure(text=s.session_id)

        self.session_id = any_to_stringvar(s.session_id)
        self.rewrite_entry(self.session_id_entry,[s.session_id])
        self.speakers = any_to_stringvar(s.speakers)
        self.rewrite_entry(self.speakers_entry,s.speakers)
        self.microphones = any_to_stringvar(s.microphones)
        self.rewrite_entry(self.microphones_entry,s.microphones) 
        self.current_speaker = None
        self.current_microphone = None   
        self.current_direction = None
        self.current_take = None
        self.current_file = None
        self.current_channel = 1
        self.plot_files = None
        self.plot_channels = "ALL"
        self.current_key = None
        self.current_plot_stats = None
        self.rtmethod = 'RT20'
        self.comment = ''
        self.pars = {}
        self.ir_list = []
        #speaker_pos = self.speaker_pos_entry.get()
        #microphone_pos = self.microphone_pos_entry.get()
        self.inchan = any_to_stringvar(s.input_channels)
        self.rewrite_entry(self.input_channels_entry,s.input_channels)        
        self.outchan = any_to_stringvar(s.output_channels)
        self.rewrite_entry(self.output_channels_entry,s.output_channels)    
        self.loopback = any_to_stringvar(s.loopback)
        self.rewrite_entry(self.loopback_entry,[s.loopback])
        self.sampling_rate = any_to_stringvar(s.sampling_rate)
        self.rtype = ""
        #self.recording_path = any_to_stringvar(s.recording_path)
        self.recording_path = s.recording_path
        self.rewrite_entry(self.recording_path_entry,[s.recording_path])
        self.sweep_file = s.sweep_file
        self.rewrite_entry(self.sweep_file_entry,[s.sweep_file])
        self.print_entries()
        self.entries_to_pars()
        print(self.pars)
        self.remove_files()
        self.load_files()
        self.tick()

    def void_recording_session(self):
        self.recording_session = None
        self.session_id = ctk.StringVar(value="")
        self.speakers = ctk.StringVar(value="")
        self.microphones = ctk.StringVar(value="")
        self.current_speaker = None
        self.current_microphone = None   
        self.current_direction = None
        self.current_take = None
        self.current_file = None
        self.current_channel = 1
        self.plot_files = None
        self.plot_channels = "ALL"
        self.current_key = None
        self.current_plot_stats = None
        self.tmax = ctk.StringVar(value="3.0")
        self.comment = ''
        self.rtmethod = 'RT20'
        self.fbankname = 'fbank'
        self.pars = {}
        self.loaded_files = []
        self.ir_list = []
        self.files = [] # list of files in recording_path
        self.logscale = ctk.StringVar(value="on")
        # check if fbankfile exists
        self.parameter_table_headers, _ = load_filterbank(self.fbankname)
        self.parameter_table_headers.insert(0,'Band')
        #speaker_pos = self.speaker_pos_entry.get()
        #microphone_pos = self.microphone_pos_entry.get()
        self.inchan = ctk.StringVar(value="")
        self.outchan = ctk.StringVar(value="")
        self.loopback = ctk.StringVar(value="")
        self.sampling_rate = ctk.StringVar(value=int(get_default_samplerate(sd.default.device[1])))
        self.rtype = ""
        self.recording_path = ""
        self.sweep_file = ""
        # load default settings
        self.input_device = ctk.StringVar(value=get_device_number_name(sd.default.device[0]))
        self.output_device = ctk.StringVar(value=get_device_number_name(sd.default.device[1]))

    def clean_recording_session(self):
        self.session_id_entry.delete(0, ctk.END)
        self.speakers_entry.delete(0, ctk.END)
        self.microphones_entry.delete(0, ctk.END)   
        # self.speaker_pos_entry.delete(0, ctk.END)
        # self.microphone_pos_entry.delete(0, ctk.END)
        self.input_channels_entry.delete(0, ctk.END)
        self.output_channels_entry.delete(0, ctk.END)
        self.loopback_entry.delete(0, ctk.END)
        self.sidebar_label_2.configure(text="")
        self.remove_files()    
        self.rewrite_textbox(self.status,f"Session cleaned")
        self.void_recording_session()
        self.create_widgets()

    def create_recording_session(self):
        # check if sesion already exists
        if self.recording_session is not None:
            print("Session already exists, please save it first and then clean.")
            self.rewrite_textbox(self.status,f"Session already exists, please save it first.")
            return
        self.print_entries()
        self.entries_to_pars()
        # check if sweepfile is present
        # Create an instance of RecordingSession
        self.recording_session = RecordingSession(
            session_id=self.pars['session_id'],
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
            sweepfile=self.sweep_file, 
            sweeprep=1
        )
        print("Session created: " + self.pars['session_id'])
        self.rewrite_textbox(self.status,f"Session created: {self.pars['session_id']}")
        self.tick()
        self.print_entries()

    def entries_to_pars(self):
        # Convert some values to their appropriate types
        self.pars['session_id'] = self.validate_entry(self.session_id_entry)
        self.pars['speakers'] = self.validate_entry(self.speakers_entry,'list')
        self.pars['microphones'] = self.validate_entry(self.microphones_entry,'list')
        self.pars['inchan'] =self. validate_entry(self.input_channels_entry,'array')
        self.pars['outchan'] = self.validate_entry(self.output_channels_entry,'array')
        self.pars['loopback'] = self.validate_entry(self.loopback_entry,'int',empty_allowed=True)
        self.pars['recording_path'] = self.validate_entry(self.recording_path_entry)
        self.pars['sweep_file'] = self.validate_entry(self.sweep_file_entry)
        self.pars['sampling_rate'] = int(self.sampling_rate.get())

    def pars_to_session(self):
        # Convert some values to their appropriate types
        self.recording_session.session_id = self.pars['session_id']
        self.recording_session.speakers = self.pars['speakers'] 
        self.recording_session.microphones = self.pars['microphones']
        self.recording_session.input_channels = self.pars['inchan']
        self.recording_session.output_channels = self.pars['outchan']
        self.recording_session.loopback = self.pars['loopback']
        self.recording_session.sampling_rate = self.pars['sampling_rate']
        self.recording_session.recording_path = self.pars['recording_path']
        self.recording_session.sweep_file = self.pars['sweep_file']


    def rewrite_entry(self, entry, value):
        entry.delete(0, ctk.END)
        entry.insert(ctk.END,','.join(map(str,value)))    

    def rewrite_textbox(self, textbox, string):    
        textbox.delete("0.0", ctk.END)
        textbox.insert(ctk.END,string)

    def print_entries(self):
        #for debugging
        print("session_id: " + self.session_id.get())
        print("speakers: " + self.speakers.get())
        print("microphones: " + self.microphones.get())
        print("inchan: " + self.inchan.get())
        print("outchan: " + self.outchan.get())
        print("loopback: " + self.loopback.get())
        print("rtype: " + self.rtype)
        if self.recording_path is not None:
            print("recording_path: " + self.recording_path)
        if self.sweep_file is not None:    
            print("sweep_file: " + self.sweep_file)
#endregion

#region AUDIO SETTINGS AND TESTING

    def save_settings(self):
        assign_device(self.input_device.get(), self.output_device.get(),int(self.sampling_rate.get()))
        self.max_chanin, self.max_chanout = get_max_channels(self.input_device.get(), self.output_device.get())
        self.rewrite_textbox(self.status,f"Settings saved")

    def test_input(self):
        # Prevent re-entry if already running
        if self._test_input_thread is not None and self._test_input_thread.is_alive():
            return
        # UI setup (safe: main thread)
        self._test_input_stop.clear()
        self.test_input_button.configure(state="disabled")
        self.test_input_bar.set(0)
        self.test_input_bar.start()
        self.rewrite_textbox(self.status, "Speak into the microphone...")
        # Start worker (background thread)
        self._test_input_thread = threading.Thread(
            target=self._test_input_worker,
            daemon=True
        )
        self._test_input_thread.start()
        self._after(50, self._poll_test_input_queue)

    def _test_input_worker(self):
        try:
            max_db = -90.0 # floor for display
            # 20 short measurements to get a stable reading
            for _ in range(20):
                if self._test_input_stop.is_set():
                    self._test_input_queue.put(("cancelled", None))
                    return

                temp = test_input_tic(
                    self.input_device.get(),
                    self.output_device.get(),
                    int(self.sampling_rate.get()),
                    dur=0.3,
                    stop_event=self._test_input_stop,
                    blocksize=1024
                )
                if self._test_input_stop.is_set():
                    self._test_input_queue.put(("cancelled", None))
                    return
                
                peak = float(np.max(np.abs(temp))) if temp.size else 0.0
                db = 20.0 * np.log10(max(peak, 1e-12))  # dBFS-like, range ~[-inf, 0]
                max_db = max(max_db, db)
                # Send progress to UI thread
                self._test_input_queue.put(("progress", max_db))

            self._test_input_queue.put(("done", max_db))
        except Exception as e:
            self._test_input_queue.put(("error", repr(e)))

    def _poll_test_input_queue(self):
        if self._closing:
            return
        finished = False
        # Drain all queued messages quickly
        try:
            while True:
                msg, payload = self._test_input_queue.get_nowait()
                if msg == "progress_db":
                    db = float(payload)
                    p = self.db_to_progress(db, db_min=-90.0, db_max=0.0) 
                    self.test_input_bar.set(p)

                elif msg == "done":
                    max_db = float(payload)
                    self.rewrite_textbox(self.status, f"Maximum input level: {max_db:.1f} dB")
                    finished = True
                    break

                elif msg == "cancelled":
                    self.rewrite_textbox(self.status, "Input test cancelled.")
                    finished = True
                    break

                elif msg == "error":
                    self.rewrite_textbox(self.status, f"Test input failed:\n{payload}")
                    finished = True
                    break
        except queue.Empty:
            pass

        if finished:
            self._finish_test_input_ui()
            return
        # Not finished yet: reschedule only if worker is still alive
        if self._test_input_thread is not None and self._test_input_thread.is_alive():
            self._after(50, self._poll_test_input_queue)
        else:
            self.rewrite_textbox(self.status, "Input test ended unexpectedly.")
            self._finish_test_input_ui()

    def _finish_test_input_ui(self):
        # cleanup UI (safe: main thread)
        self.test_input_bar.stop()
        self.test_input_bar.set(0)
        self.test_input_button.configure(state="normal")

    def db_to_progress(db, db_min=-90.0, db_max=0.0):
        # Map db_min -> 0, db_max -> 1
        p = (db - db_min) / (db_max - db_min)
        return float(np.clip(p, 0.0, 1.0))

    def test_output(self):
        # Prevent re-entry
        if self._test_output_thread is not None and self._test_output_thread.is_alive():
            return
        self._test_output_stop.clear()
        self.test_output_button.configure(state="disabled")
        self.rewrite_textbox(self.status, "Playing output signal...")
        # Start worker thread
        self._test_output_thread = threading.Thread(
            target=self._test_output_worker,
            daemon=True
        )
        self._test_output_thread.start()
        # Start polling
        self._after(50, self._poll_test_output_queue)

    def _test_output_worker(self):
        try:
            if self._test_output_stop.is_set():
                self._test_output_queue.put(("cancelled", None))
                return
            test_output_tic(
                self.input_device.get(),
                self.output_device.get(),
                int(self.sampling_rate.get()),
                stop_event=self._test_output_stop
            )
            if self._test_output_stop.is_set():
                self._test_output_queue.put(("cancelled", None))
            else:
                self._test_output_queue.put(("done", None))
        except Exception as e:
            self._test_output_queue.put(("error", repr(e)))

    def _poll_test_output_queue(self):
        if self._closing:
            return
        try:
            msg, payload = self._test_output_queue.get_nowait()
        except queue.Empty:
            # Still working → poll again
            if self._test_output_thread is not None and self._test_output_thread.is_alive():
                self._after(50, self._poll_test_output_queue)
            return
        self.test_output_button.configure(state="normal")
        if msg == "done":
            self.rewrite_textbox(self.status, "Output signal played.")
        elif msg == "cancelled":
            self.rewrite_textbox(self.status, "Output test cancelled.")
        elif msg == "error":
            self.rewrite_textbox(self.status, f"Test output failed: {payload}")

#endregion

#region RECORDING

    def start_recording(self):
        print("start recording")
        if self.recording_session is None:
            self.rewrite_textbox(self.status, "No session created/loaded.")
            return
        if self._busy:
            self.rewrite_textbox(self.status, "Recording already running.")
            return
        self._busy = True
        self.start_recording_button.configure(state="disabled")  # exists in UI? 
        self.button_quit.configure(state="disabled")             # optional safety
        self.rewrite_textbox(self.status, "Recording starting, please wait...")

        #self.status.update_idletasks() 
        self.current_speaker = self.speaker_box.get()
        self.current_microphone = self.microphone_box.get()
        self.current_direction = self.direction_box.get()
        self.current_take = self.take_box.get()
        self.comment = self.comment_entry.get()
        textinfo=f"Parlante {self.current_speaker}, Microfono {self.current_microphone}, Direccion {self.current_direction}, Toma {self.current_take}"
        # Start worker thread
        args = (self.current_speaker, self.current_microphone,
            self.current_direction, self.current_take, self.comment, textinfo)
        
        self._worker_thread = threading.Thread(target=self._record_ir_worker,args=args,daemon=True)
        self._worker_thread.start()

        # Start polling for completion
        self._after(100, self._poll_recording_worker)     
      
    def _record_ir_worker(self, speaker, microphone, direction, take, comment, textinfo):
        try:
            ir_temp = self.recording_session.record_ir(
                speaker, microphone, direction, take, comment
            )
            # Send success back to UI thread
            self._worker_queue.put(("ok", ir_temp, textinfo))
        except Exception:
            # Send error back to UI thread
            self._worker_queue.put(("err", traceback.format_exc(), textinfo))

    def _poll_recording_worker(self):
        try:
            msg = self._worker_queue.get_nowait()
        except queue.Empty:
            # Still working → poll again
            self._after(100, self._poll_recording_worker)
            return

        kind, payload, textinfo = msg

        # Re-enable controls (always)
        self._busy = False
        self.start_recording_button.configure(state="normal")
        self.button_quit.configure(state="normal")

        if kind == "err":
            self.rewrite_textbox(self.status, f"Recording failed:\n{payload}")
            return

        # Success: payload is ir_temp
        ir_temp = payload
        self.rewrite_textbox(self.status, f"Finished -> {textinfo}")
        self.add_file()

        fs = ctkstring_to_value(self.sampling_rate, type="int")
        ir_plot(
            ir_temp[:, 0],
            fs=fs,
            tmax=float(self.tmax.get()),
            axs=self.matplotlib_ir_axes
        )
        self.matplotlib_ir_frame.canvas.draw()
        self.matplotlib_ir_frame.canvas.flush_events()
#endregion

#region DATA FILES        

    def load_files(self):
        print("load files")
        print(self.recording_session)
        print(self.recording_session.recordings)
        for n,rec in enumerate(self.recording_session.recordings):
            fname = rec['filename']
            self.data_table.add_row([[fname],rec['spk'],rec['mic'],rec['dir'],rec['take'],rec['nchan']])
            self.files.append(fname)

    def add_file(self):
        print("add file")
        fname = self.recording_session.recordings[-1]['filename']
        nchan = self.recording_session.recordings[-1]['nchan']
        self.data_table.add_row([[fname],self.current_speaker,self.current_microphone,self.current_direction,self.current_take,[nchan]])
        self.files.append(fname)

    def remove_files(self):
        nrows = self.data_table.rows
        for n in range(nrows-1,0,-1):
            self.data_table.delete_row(n)
        self.files = []
        pass

    def load_irs(self):
        selected_indices = self.data_table.get_checked_indices()
        print("Selected indices:", selected_indices)
        self.ir_list = self.recording_session.load_ir_list(selected_indices,ftype='npy')
        self.list_files = [self.recording_session.recordings[n]['filename'] for n in selected_indices]
        self.list_nchan = [self.recording_session.recordings[n]['nchan'] for n in selected_indices]
        self.list_comment = [self.recording_session.recordings[n]['comment'] for n in selected_indices]
        filenames = [' '.join(f.split('_')[1:4]) for f in self.list_files]
        self.rewrite_textbox(self.status,f"Files: {filenames}")
        self.tick()    

    def set_channel(self,file):
        nchannels = self.list_nchan[self.list_files.index(file)]
        self.select_channel_box.configure(values=[str(n+1) for n in np.arange(nchannels)])
        self.select_channel_box.set('1')
        self.select_channel_box_s.configure(values=[str(n+1) for n in np.arange(nchannels)])
        self.select_channel_box_s.set('1')
        self.select_channel_box_t.configure(values=[str(n+1) for n in np.arange(nchannels)])
        self.select_channel_box_t.set('1')
        self.select_channel_box_d.configure(values=[str(n+1) for n in np.arange(nchannels)])
        self.select_channel_box_d.set('1')

    def set_plot_channels(self, plotfile):
        if len(self.ir_list) == 0:
            print("There are no IRs loaded")
            self.rewrite_textbox(self.status,f"There are no IRs loaded")
            return
        if plotfile == "ALL":
            nchannels = min(self.list_nchan)
            self.select_channel_box_p.configure(values=[str(n+1) for n in np.arange(nchannels)])
            self.select_channel_box_p.set('1')
        else:
            nchannels = self.list_nchan[self.list_files.index(plotfile)]
            self.select_channel_box_p.configure(values=["ALL"] + [str(n+1) for n in np.arange(nchannels)])
            self.select_channel_box_p.set("ALL")
            #self.set_channel(plotfile) # why is this needed?

    def set_method(self,method):
        self.rtmethod = method
        self.parameter_plot_keys = [self.rtmethod,'EDT','C50','C80','TS','DRR','SNR']
        self.select_key_box.configure(values=self.parameter_plot_keys)
        self.select_key_box.set(self.rtmethod)
        self.parameter_table_keys = ['Band',self.rtmethod,'rvalue','EDT','C50','C80','TS','DRR','SNR']
        self.parameter_table.edit_column(column=0,values=self.parameter_table_keys)
#endregion

#region ROOM ACOUSTICS
    def analyze(self):
        if len(self.ir_list) == 0:
            print("There are no IRs loaded")
            self.rewrite_textbox(self.status,f"There are no IRs loaded")
            return
        self.plot_files = self.select_file_box_p.get()
        self.plot_channels = self.select_channel_box_p.get()
        self.rewrite_textbox(self.status,f"Computing parameters using filterbank {self.fbankname}")
        
        if self.plot_files == 'ALL': 
            if self.plot_channels == 'ALL':
                # case 1 all files, single channel not supported yet default to channel 0
                self.ir_stacked = ir_list_to_multichannel(self.ir_list)
                self.params = paracoustic(self.ir_stacked, method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))
                labels = [' '.join(f.split('_')[1:4]) for f in self.list_files]
            else :    
                # case 2 all files, single channel
                chan = int(self.plot_channels)-1
                # build a multichannel IR from ir_list using the specified channel
                self.ir_stacked = ir_list_to_multichannel(self.ir_list,chan=chan)
                self.params = paracoustic(self.ir_stacked, method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))
                labels = [' '.join(f.split('_')[1:4]) + ' ch ' + self.plot_channels for f in self.list_files]
        else:
            ir = self.ir_list[self.list_files.index(self.plot_files)]
            if self.plot_channels == 'ALL':
                # case 3 single file, all channels
                self.params = paracoustic(ir, method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))
                labels = [' '.join(self.plot_files.split('_')[1:4]) + ' ch ' + str(n) for n in range(ir.shape[1])]
            else:
                # case 4 single file, single channel
                chan = int(self.plot_channels)-1
                self.params = paracoustic(ir[:,chan], method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))
                labels = [' '.join(self.plot_files.split('_')[1:4]) + ' ch ' + self.plot_channels]
        self.current_key = self.select_key_box.get()
        self.plot_params(self.current_key,labels)
        return

    def display_params(self,channel=0):
        # table for channel =0 and index = idx  
        self.current_file = self.select_file_box.get()
        self.current_channel = int(self.select_channel_box.get())-1
        ir = self.ir_list[self.list_files.index(self.current_file)]
        self.comment = self.list_comment[self.list_files.index(self.current_file)]
        self.comment_box.delete('1.0',ctk.END)
        self.comment_box.insert(ctk.END,self.comment)
        self.rewrite_textbox(self.status,f"Computing parameters of {self.current_file} using filterbank {self.fbankname}")
        self.params = paracoustic(ir, method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))
        for row,key in enumerate(self.parameter_table_keys):
            if row>0:
                for col in range(1,self.parameter_table.columns):
                    self.parameter_table.insert(row, col, self.params[key][col-1,self.current_channel].round(decimals=2))
        return
    
    def save_table(self):
        fname = self.current_file.split('.')[0] + "chan_" + str(self.current_channel) + ".csv"
        file = open(fname, 'w')
        print(f"Saving parameters to {fname}")
        self.rewrite_textbox(self.status,f"Saving parameters to {fname}")
        writer = csv.writer(file)
        writer.writerow(self.parameter_table_headers)
        for row,key in enumerate(self.parameter_table_keys):
            if (row > 0):
                    writer.writerow([key] + list(self.params[key][:,self.current_channel].round(decimals=2)))
        file.close()           
#endregion
    
#region PLOTS
# TODO: move to a separate class

    def plot_params(self,key,labels):
        if self.params is not None:  
            pars_compared_axes(self.params, key, self.matplotlib_analysis_axes,labels=labels)
            self.matplotlib_analysis_frame.canvas.draw()
            self.matplotlib_analysis_frame.canvas.flush_events()

    def plot_stats(self):
        # check if there are IRs loaded
        if len(self.ir_list) == 0:
            print("There are no IRs loaded")
            self.rewrite_textbox(self.status,f"Load some IRs first")
            return
        self.current_plot_stats = self.select_plot_stats_box.get()
        self.current_file = self.select_file_box_s.get()
        ir = self.ir_list[self.list_files.index(self.current_file)]
        fs = ctkstring_to_value(self.sampling_rate, type='int')
        self.current_channel = int(self.select_channel_box_s.get())-1
        redraw = (self.plot_stats_overlay.get()=="off")
        labels = [' '.join(self.current_file.split('_')[1:4]) + ' ch ' + str(self.current_channel+1)]
        self.rewrite_textbox(self.status,f"Plotting {self.current_plot_stats} of {self.current_file}")
        if (self.current_plot_stats == "IR Plot"):
            #plot IR
            ir_plot(ir[:,self.current_channel],fs=fs, tmax=float(self.tmax.get()), redraw=redraw, \
                    labels=labels, axs=self.matplotlib_stats_axes)
            self.matplotlib_stats_frame.canvas.draw()
            self.matplotlib_stats_frame.canvas.flush_events()
        elif (self.current_plot_stats == "IR Stats"):    
            #plot stats
            irstat_plot(ir[:,self.current_channel], window=0.01, overlap=0.002, fs=fs, logscale=True, \
                        tmax=float(self.tmax.get()),axs=self.matplotlib_stats_axes)
            self.matplotlib_stats_frame.canvas.draw()
            self.matplotlib_stats_frame.canvas.flush_events()
        elif (self.current_plot_stats == "IR Echo"):    
            #plot echogram
            echo_display(ir[:,self.current_channel], 7, pw=0.7, scale=0.1, wplot=True, fs=fs, \
                         redraw=redraw, labels=labels, axs=self.matplotlib_stats_axes)
            self.matplotlib_stats_frame.canvas.draw()
            self.matplotlib_stats_frame.canvas.flush_events()    
        else:
            raise ValueError("Plot type not recognized")
        return  
    
    def plot_transfer(self):
        self.current_file = self.select_file_box_t.get()
        ir = self.ir_list[self.list_files.index(self.current_file)]
        fs = ctkstring_to_value(self.sampling_rate, type='int')
        self.current_channel = int(self.select_channel_box_t.get())-1
        self.logscale = (self.plot_transfer_log.get()=="on")
        overlay = (self.plot_transfer_overlay.get()=="on")
        labels = [' '.join(self.current_file.split('_')[1:4]) + ' ch ' + str(self.current_channel+1)]
        print(self.logscale)
        self.rewrite_textbox(self.status,f"Computing Transfer Function of {self.current_file}")
        spectrum_plot(ir[:,self.current_channel],logscale=self.logscale, fs=fs, overlay=overlay, axs=self.matplotlib_transfer_axes,   
                      labels= labels)
        self.matplotlib_transfer_frame.canvas.draw()
        self.matplotlib_transfer_frame.canvas.flush_events()
        return

    def plot_decays(self):
        self.current_file = self.select_file_box_d.get()
        ir = self.ir_list[self.list_files.index(self.current_file)]
        fs = ctkstring_to_value(self.sampling_rate, type='int')
        self.current_channel = int(self.select_channel_box_d.get())-1
        self.rewrite_textbox(self.status,f"Computing Decays of {self.current_file} using filterbank {self.fbankname}")
        self.params = paracoustic(ir, method=self.rtmethod,bankname=self.fbankname,tmax=float(self.tmax.get()))      
        _, fig = parsdecay_plot(self.params, chan=self.current_channel, fs=fs)
        img = figure_to_image(fig,width=900,height=500)
        self.image_decay_frame.configure(image=img)
        return
#endregion

#region UPDATE AND STOP METHODS

    def update_window(self):
        if self.pars:
            self.speaker_box.configure(values=self.pars['speakers'])
            self.microphone_box.configure(values=self.pars['microphones'])
            if self.pars['speakers']:
                self.speaker_box.set(self.pars['speakers'][0])
            if self.pars['microphones']:
                self.microphone_box.set(self.pars['microphones'][0])
        if len(self.ir_list) > 0:
            self.select_file_box.configure(values=self.list_files)
            self.select_file_box.set(self.list_files[0])
            self.select_file_box_s.configure(values=self.list_files)
            self.select_file_box_s.set(self.list_files[0])
            self.select_file_box_t.configure(values=self.list_files)
            self.select_file_box_t.set(self.list_files[0])
            self.select_file_box_d.configure(values=self.list_files)
            self.select_file_box_d.set(self.list_files[0])
            self.select_file_box_p.configure(values=["ALL"] + self.list_files)
            self.select_file_box_p.set("ALL")
            self.select_method_box.set(self.rtmethod) 
            self.select_channel_box.set(self.current_channel+1)
            self.select_channel_box_s.set(self.current_channel+1)
            self.select_channel_box_t.set(self.current_channel+1)
            self.select_channel_box_d.set(self.current_channel+1)
            self.select_channel_box_p.set(self.plot_channels)
        self.sidebar_label_2.configure(text=self.session_id.get())
        self.root.update_idletasks()
        
    def tick(self):
        self.root.update()
        self.update_window()

    def stops(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True

        if getattr(self, "_busy", False):
            self.rewrite_textbox(self.status, "Recording in progress. Please wait until it finishes.")
            return
        print("Stopping")
        self.save_and_close = True
        try:
            self._test_input_stop.set()
        except Exception:
            pass
        try:
            self._test_output_stop.set()
        except Exception:
            pass
        # stop any sounddevice streams
        try:
            sd.stop()
        except Exception:
            pass
        # cancel scheduled callbacks
        self._after_cancel_all()    
        # exits mainloop
        try:
            self.root.quit()     
        except Exception:
            pass
        # destroy window    
        try:
            self.root.destroy()
        except Exception:
            pass

    def _after(self, ms, func, *args):
        """Schedule a callback and track its ID so it can be cancelled on shutdown."""
        if self._closing:
            return None
        after_id = self.root.after(ms, func, *args)
        self._after_ids.add(after_id)
        return after_id

    def _after_cancel_all(self):
        """Cancel all tracked callbacks (best-effort)."""
        for after_id in list(self._after_ids):
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        self._after_ids.clear()

#endregion

#region VALIDATION METHODS
  
    def validate_entry(self,entry, type='string', empty_allowed=False):
        """
        Validate the entry based on the type.
        """
        value = entry.get()
        if type == 'int':
            if value == "" and empty_allowed:
                return None
            try:
                s = int(value)
                return s
            except ValueError:
                self.rewrite_textbox(self.status,f"{entry} must be an integer")
                return
        elif type == 'float':
            try:
                s = float(value)
                return s
            except ValueError:
                self.rewrite_textbox(self.status,f"{entry} must be a float")
                return
        elif type == 'array':
            if value == "" and empty_allowed:
                return None
            try:
                s = [int(x.strip()) for x in value.split(',')]
                return s
            except ValueError:
                self.rewrite_textbox(self.status,f"{entry} must be a list of integers separated by commas")
                return
        elif type == 'list':
            if value == "" and empty_allowed:
                return None
            try:
                s = [x.strip() for x in value.split(',')]
                return s
            except ValueError:
                self.rewrite_textbox(self.status,f"{entry} must be a list of strings separated by commas")
                return
        else:
            if isinstance(value, str):
                if value == "" and empty_allowed:
                    return None
                return value
#endregion            