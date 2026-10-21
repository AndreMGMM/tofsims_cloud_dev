"""Run from this folder with: python main.py"""
import os
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
from nicegui import ui
import gui.layout  # registers browser pages

if __name__ == '__main__':
    ui.run(host='0.0.0.0',port=8080,reload=False,show=False,title='ToF-SIMS Cloud Dev')
