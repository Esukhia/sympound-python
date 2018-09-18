#! /usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import print_function

import os
import sys
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="sympound",
    version="0.6.0",  #edit version in __init__.py
    author="Esukhia development team",
    author_email="esukhiadev@gmail.com",
    description="Python implementation of SymSpell Compound",
    license="MIT",
    keywords="spell check",
    url="https://github.com/Esukhia/sympound-python",
    packages=find_packages(),
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    project_urls={
        'Source': 'https://github.com/Esukhia/sympound-python',
        'Tracker': 'https://github.com/Esukhia/sympound-python/issues',
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires='>=3',
)
