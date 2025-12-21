from irma.gui_ctk import IRMA_ctk
from pathlib import Path
# -*- coding: utf-8 -*-
from irma.process import make_filterbank    

def main():
    # start audio
    # read configuration file fs
    fs = 48000
    # create filter bank
    make_filterbank(fs = fs,bankname='fbank')
    # create windows
    app = IRMA_ctk()
    #app.root.mainloop()
    while app.save_and_close == False:
        app.root.update()


if __name__ == "__main__":
    main()
    