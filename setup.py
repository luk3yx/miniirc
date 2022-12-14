#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name='miniirc',
    version='1.9.1',
    py_modules=['miniirc'],
    author='luk3yx',
    description='A lightweight IRC framework.',
    url='https://github.com/luk3yx/miniirc',
    license='MIT',

    long_description=desc,
    long_description_content_type='text/markdown',
    install_requires=['certifi>=2020.4.5.1'],
    python_requires='>=3.4',

    classifiers=[
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries',
    ]
)
