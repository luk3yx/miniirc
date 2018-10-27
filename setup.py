#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc',
    version     = '0.2.6',
    py_modules  = ['miniirc'],
    author      = 'luk3yx',
    description = 'A lightweight IRC framework.',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['certifi'],

    classifiers = [
        'Intended Audience :: Developers',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ]
)
