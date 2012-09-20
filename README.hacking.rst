Welcome!

There are three ways the Park unit test suite is run.

As a *developer*, use ``python setup.py test``. This runs the suite in
the current development directory and does not require a virtualenv to
be set up.

As a *contributor*, your Github pull requests will be tested on Travis
CI. The configuration for that is in .travis.yml. This runs the test
suite on all supported platforms, which are enumerated in that file.

As a *release maintainer*, install ``tox`` (in a virtualenv is fine)
and run it in the top level Park source directory. This will build a
source distribution, install that into a virtualenv for each supported
platform, and run the test suite in each.

