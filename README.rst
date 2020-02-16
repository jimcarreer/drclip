Docker Registry CLI with Python |build-status| |cover-status|
=============================================================

This project provides a click based CLI interface against the version 2 docker registry API.  I wrote this because
Google yielded nothing, and I run a private registry for personal projects that needs maintenance that is extremely
cumbersome with curl / bash scripts.

Installation
------------
I haven't put this in pypi yet, so you can just pull and install with pip:

.. code-block:: bash

    $ git pull https://github.com/jimcarreer/drclip.git
    $ cd drclip
    $ pip install . -U

Supported Python Versions
  * 3.6
  * 3.7
  * 3.8

Usage
-----
The tool makes use of the fantastic Click library with a sub command structure:

.. code-block:: bash

    $ drclip --help
    Usage: drclip [OPTIONS] COMMAND [ARGS]...

    Options:
      -c, --config FILENAME
      -r, --registry TEXT    The registry to query
      --help                 Show this message and exit.

    Commands:
      repos  Lists the repositories in a registry via the _catalog API
      tags   Lists the tags for a given repository using the /tags/list API


After installation you can enable tab completion with bash via:

.. code-block:: bash

    $ eval "$(_DRCLIP_COMPLETE=source drclip)"


Credentials for the registries are retrieved (by default) by using the :code:`~/.docker/config.json`.  Currently only
the built in credential store system provided by docker is supported for retrieving credentials.

.. |build-status| image:: https://api.travis-ci.org/jimcarreer/drclip.svg?branch=master
   :target: https://travis-ci.org/jimcarreer/drclip
.. |cover-status| image:: https://codecov.io/gh/jimcarreer/drclip/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/jimcarreer/drclip
.. role:: bash(code)
   :language: bash