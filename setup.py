#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012 Raphaël Barrois

from distutils.core import setup
from distutils import cmd
import os
import re

def get_version():
    version_re = re.compile(r"^__version__ = '([\w_.]+)'$")
    with open(os.path.join(os.path.dirname(__file__), 'palm2vcal', '__init__.py')) as f:
        for line in f:
            match = version_re.match(line[:-1])
            if match:
                return match.groups()[0]
    return '0.0'


def readfile(filename):
    with open(filename, 'r') as f:
        return f.read()


setup(
    name='palm2vcal',
    version=get_version(),
    description="Convert PalmOS .dba calendar to a vcalendar file.",
    long_description=readfile('README'),
    author='Raphaël Barrois',
    author_email='raphael.barrois@polytechnique.org',
    url='http://github.com/rbarrois/palm2vcal',
    download_url="http://pypi.python.org/pypi/palm2vcal/",
    keywords=['palm', 'calendar', 'conversion', 'vcalendar', 'ics'],
    packages=['palm2vcal'],
    scripts=['bin/palm2vcal'],
    license='MIT',
    requires=[
        'icalendar',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Office/Business :: Scheduling',
    ],
)


