#!/usr/bin/env python
# coding: utf-8

import sys

# Require setuptools. See http://pypi.python.org/pypi/setuptools for
# installation instructions, or run the ez_setup script found at
# http://peak.telecommunity.com/dist/ez_setup.py
from setuptools import setup, find_packages


setup(
    name="park",
    version="1.0.0",
    author="Peter Teichman",
    author_email="pteichman@litl.com",
    license="MIT",
    description="A key-value store with ordered traversal of keys",
    py_modules=["park"],
    test_suite="test_park",

    setup_requires = [
        "unittest2==0.5.1"
        ]
)
