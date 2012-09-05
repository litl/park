#!/usr/bin/env python
# coding: utf-8

import sys

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages, Command

class CheckCommand(Command):
    description = "Run tests."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        print "Running pep8..."
        if subprocess.call(["pep8", "park.py", "test_park.py"]):
            sys.exit("ERROR: failed pep8 checks")

        print "Running pyflakes..."
        if subprocess.call(["pyflakes", "park.py", "test_park.py"]):
            sys.exit("ERROR: failed pyflakes checks")

        print "Running tests..."
        if subprocess.call(["coverage", "run", "--source=park,test_park",
                            "./setup.py", "test"]):
            sys.exit("ERROR: failed unit tests")

        subprocess.call(['coverage', 'report', '-m'])


setup(
    name="park",
    version="0.9.0",
    author="Peter Teichman",
    author_email="pteichman@litl.com",
    license="MIT",
    url = "https://github.com/litl/park",
    description="A key-value store with ordered traversal of keys",
    py_modules=["park"],
    test_suite="test_park",

    cmdclass = {
        "check": CheckCommand
        },

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python"
        ]
)
