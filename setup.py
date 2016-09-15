#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='GMesh',
    version='0.0.1',
    description='Various meshing tools',
    author='Eivind Fonn',
    author_email='eivind.fonn@sintef.no',
    license='GPL3',
    url='https://github.com/TheBB/gmesh',
    packages=['gmesh', 'gmesh.utm'],
    scripts=['rungmesh'],
)
