#! /usr/bin/env python

from setuptools import setup, find_packages

setup(name='pygel',
      version='0.6.4',
      author='Marcelo Aires Caetano',
      author_email='marcelo@fiveti.com',
      license='BSD',
      keywords='event library, file monitor, watchdog',
      description='An implementation of some functionalities of gobject/glib/gio in pure python, but adding a lot of new features.',
      long_description=open('README.txt').read(),
      packages=find_packages(),
      install_requires=['socketqueue>=0.1.9', 'six>=1.10.0'],
      url='http://github.com/caetanus/pygel')
