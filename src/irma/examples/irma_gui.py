from irma.gui_ctk import IRMA_ctk
from pathlib import Path
# -*- coding: utf-8 -*-
from irma.process import make_filterbank    

def main():
    #inicia audio
    # lee archivo de configuracion fs
    fs = 48000
    # crea banco de filtros
    if not Path('fbank.npz').is_file:
        # si no existe el banco de filtros, lo crea 
        make_filterbank(fs = fs,bankname='fbank')
    # Crea Ventanas
    app = IRMA_ctk()
    #app.root.mainloop()
    while app.save_and_close == False:
        app.root.update()


if __name__ == "__main__":
    main()
    