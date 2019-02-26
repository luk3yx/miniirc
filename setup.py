#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc',
    version     = '1.0.8',
    py_modules  = ['miniirc'],
    author      = 'luk3yx',
    description = 'A lightweight IRC framework.',
    url         = 'https://github.com/luk3yx/miniirc',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['certifi'],

    classifiers = [
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ]
)
