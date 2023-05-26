from acousticfield.gui_ctk import *

def main():
    app = Acousticfield_ctk()
    #inicia audio
    # Crea Ventanas
    #app.root.mainloop()
    while app.save_and_close == False:
        app.root.update()


if __name__ == "__main__":
    main()
    