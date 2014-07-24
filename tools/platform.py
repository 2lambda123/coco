#!/usr/bin/env python2.7
## -*- mode: python -*-

## Lots of utility functions to abstract away platform differences.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
from shutil import copyfile
from subprocess import CalledProcessError, check_output, call, STDOUT

def hg(args):
    """Run a Mercurial command and return its output. 

    All errors are deemed fatal and the system will quit."""
    full_command = ['hg']
    full_command.extend(args)
    try:
        output = check_output(full_command, env=os.environ).rstrip()
    except CalledProcessError as e:
        print('Failed to execute hg.')
        sys.exit(-1)
    return output

def is_dirty():
    """Return True if the current working copy has uncommited changes."""
    return hg(['hg', 'id', '-i'])[-1] == '+'

def hg_version():
    """ Derive the current version number from the latest tag and the
    number of (local) commits since the tagged revision. """
    return hg(['log', '-r', '.', '--template', '{latesttag}.{latesttagdistance}'])

def hg_revision():
    return hg(['id', '-i'])

def run(directory, args):
    print("RUN\t%s in %s" % (" ".join(args), directory))
    oldwd = os.getcwd()
    try:
        os.chdir(directory)
        output = check_output(args, stderr=STDOUT, env=os.environ)
    except CalledProcessError as e:
        print("ERROR in platform.run: return value=%i" % e.returncode)
        print(e.output)
        sys.exit(-1)
    finally:
        os.chdir(oldwd)

def python2(directory, args, env=None):
    print("PY2\t%s in %s" % (" ".join(args), directory))
    oldwd = os.getcwd()
    full_command = ['python2']
    ## OME: Need Python 2.7 for NumPy.
    # full_command = ['python']
    full_command.extend(args)
    try:
        os.chdir(directory)
        output = check_output(full_command, stderr=STDOUT, env=os.environ)
    except CalledProcessError as e:
        print("ERROR in platform.python2: return value=%i" % e.returncode)
        print(e.output)
        raise
        sys.exit(-1)
    finally:
        os.chdir(oldwd)

def python3(directory, args, env=None):
    print("PY3\t%s in %s" % (" ".join(args), directory))
    oldwd = os.getcwd()
    full_command = ['python3']
    ## OME: Need Python 2.7 for NumPy.
    # full_command = ['python']
    full_command.extend(args)
    try:
        os.chdir(directory)
        output = check_output(full_command, stderr=STDOUT, env=os.environ)
    except CalledProcessError as e:
        print("ERROR in platform.python3: return value=%i" % e.returncode)
        print(e.output)
        raise
        sys.exit(-1)
    finally:
        os.chdir(oldwd)

def copy_file(source, destination):
    print("COPY\t%s -> %s" % (source, destination))
    copyfile(source, destination)

def write_file(string, destination):
    print("WRITE\t%s" % destination)
    with open(destination, "w") as fd:
        fd.write(string.decode())  # decode bytes type to string

def make(directory, target):
    """Run make to build a target"""
    print("MAKE\t%s in %s" % (target, directory))
    oldwd = os.getcwd()
    try:
        os.chdir(directory)
        output = check_output(['make', target], stderr=STDOUT, env=os.environ)
    except CalledProcessError as e:
        print("ERROR: return value=%i" % e.returncode)
        print(e.output)
        sys.exit(-1)
    finally:
        os.chdir(oldwd)

def expand_file(source, destination, dictionary):
    print("EXPAND\t%s to %s" % (source, destination))
    from string import Template
    with open(source, "r") as fd:
        content = Template(fd.read())        
        with open(destination, "w") as outfd:
            outfd.write(content.safe_substitute(dictionary))

