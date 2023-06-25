from irma.gui_ctk import *
from irma.process import make_filterbank

def main():
    #inicia audio
    # lee archivo de configuracion fs
    fs = 48000
    # crea banco de filtros
    make_filterbank(fs = fs,bankname='fbank')
    # Crea Ventanas
    app = Acousticfield_ctk()
    #app.root.mainloop()
    while app.save_and_close == False:
        app.root.update()


if __name__ == "__main__":
    main()
    