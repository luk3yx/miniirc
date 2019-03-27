#!/usr/bin/python2

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc',
    version     = '1.1.3.post2',
    py_modules  = ['miniirc'],
    author      = 'luk3yx',
    description = 'A lightweight IRC framework.',
    url         = 'https://github.com/luk3yx/miniirc',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['certifi'],
    python_requires               = '==2.7.*',

    classifiers = [
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
    ]
)
