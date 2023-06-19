# acousticfield
Tools for soundscape / acoustic field / recording, processing and analysis

## Instalation with Anaconda (jun 2023)
base:
- python >= 3.9.13
- numpy >= 1.21.5
- scipy >= 1.9.1
- matplotlib >= 3.5.2
- ipython >= 7.31.1
- pyyaml >= 6.0

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

## acousticfield

Download the latest dist or install via pip with

`pip install -i https://test.pypi.org/simple/ acousticfield --no-deps`

## Usage

Two jupyter notebooks (still in spanish) provide the basics for interactive use

`notebooks/test_acousticfield.ipynb`

and for a session-based operation:

`notebooks/field_session.ipynb`

## GUI

A GUI using [customtkinter](https://github.com/tomschimansky/customtkinter) is under development.

If you want to give a try you will need:

- matplotlib >= 3.7
- customtkinter >= 5.1

And then you can run the example with

`python examples/acousticfield_gui.py`
