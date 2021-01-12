# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 12:57:28 2020

@author: danie
"""
import os
from pathlib import Path
import sys

def activate():
    python_exe = Path(sys.executable)
    python_env = python_exe.parent
    print(f"setting environment {python_env}")

    env = os.environ
    
    env['PATH'] = ('{python_env};'
                    '{python_env}\\Library\\mingw-w64\\bin;'
                    '{python_env}\\Library\\usr\\bin;'
                    '{python_env}\\Library\\bin;'
                    '{python_env}\\Scripts;'
                    '{python_env}\\bin;'
                    '{path}').format(path=env['PATH'],
                                    python_env=python_env
    )
    env['VIRTUAL_ENV'] = str(python_env)


if __name__ == '__main__':
    activate()
