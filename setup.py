# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import pkg_resources  # part of setuptools


from fewsbokeh import __version__,__description__

#%%
with open('README.md', encoding='utf8') as f:
    long_description = f.read()

setup(
    name='fewsbokeh',
    version=__version__,
    description=__description__,
    long_description=long_description,
    url='https://github.com/d2hydro/fewsbokeh',
    author='Daniel Tollenaar',
    author_email='daniel@d2hydro.nl',
    license='MIT',
    packages=find_packages(),
    #packages=['fewsbokeh'],
    python_requires='>=3.6',
    install_requires=[
        'pandas',
        'bokeh'
    ],
    keywords='bokeh FEWS REST',
)
