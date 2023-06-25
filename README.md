# IR-ma (Impulse Response Measurement and Analysis)
a.k.a. acousticfield
Tools for acoustic field measurement and analysis
based on the the Impulse Response

## Instalation with Anaconda (jun 2023)
base:
- numpy >= 1.24
- scipy >= 1.10
- matplotlib >= 3.7
- pyyaml >= 6.0
- ipython >= 8.12
- python-sounddevice >= 0.4.6

## python sounddevice
For linux, mac, or windows without ASIO or OSX/Linux

`conda install -c conda-forge python-sounddevice`
 
or, using pip:

`pip install python-sounddevice`

For windows with ASIO support:

Install latest version (0.4.5) from
https://readthedocs.org/projects/python-sounddevice/downloads/pdf/latest/

using the most recent package from 
https://www.lfd.uci.edu/~gohlke/pythonlibs/#sounddevice

for example:
`pip install sounddevice‑0.4.4‑pp38‑pypy38_pp73‑win_amd64.whl`


## Usage

Two jupyter notebooks (still in spanish) provide the basics for interactive use

`notebooks/test_irma.ipynb`

and for a session-based operation:

`notebooks/field_session.ipynb`

## GUI

A GUI using [customtkinter](https://github.com/tomschimansky/customtkinter) is under development.

If you want to give a try you will need:

- matplotlib >= 3.7
- customtkinter >= 5.1

And then you can run the example with

`python examples/irma_gui.py`
