Docker Registry CLI with Python
===============================
|build-status| |cover-status| |pyver-status| |pypiv-status|

This project provides a click based CLI interface against the version 2 docker registry API.  I wrote this because
Google yielded nothing, and I run a private registry for personal projects that needs maintenance that is extremely
cumbersome with curl / bash scripts.

Installation
------------
We're now available in pypi! Install simply with:

.. code-block::

    $ pip install drclip

Usage
-----
The tool makes use of the fantastic Click library with a sub command structure:

.. code-block::

    $ drclip --help

    Usage: drclip [OPTIONS] COMMAND [ARGS]...

      Runs commands against docker registries

    Options:
      -c, --config FILENAME
      -r, --registry TEXT    The registry to query  [required]
      --help                 Show this message and exit.

    Commands:
      digests   Get the digest(s) for given tag(s)
      manifest  List the manifests for a given repository and a given tag
      repos     Lists the repositories in a registry via the _catalog API
      rmd       Removes a manifest(s) for given digest(s)
      tags      Lists the tags for a given repository using the /tags/list API

Tab completion
**************
After installation you can enable tab completion with bash via:

.. code-block::

    $ eval "$(_DRCLIP_COMPLETE=source drclip)"

Right now only the :code:`-r` / :code:`--registry` option supports tab completion.

Environs
********
There are a couple of environmental variables you can define to avoid tedious argument entry:

* :code:`DRCLIP_REG` - defaults the :code:`-r` / :code:`--registry` argument on commands
* :code:`DRCLIP_REPO` - defaults the :code:`-o` / :code:`--repository` argument on commands


Authentication
**************
Credentials for the registries are retrieved (by default) by using the :code:`~/.docker/config.json`.  Currently only
the built in credential store system provided by docker is supported for retrieving credentials.

.. |build-status| image:: https://api.travis-ci.org/jimcarreer/drclip.svg?branch=master
   :target: https://travis-ci.org/jimcarreer/drclip
.. |cover-status| image:: https://codecov.io/gh/jimcarreer/drclip/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/jimcarreer/drclip
.. |pyver-status| image:: https://img.shields.io/pypi/pyversions/drclip
   :target: https://pypi.org/project/drclip/
.. |pypiv-status| image:: https://badge.fury.io/py/drclip.svg?dummy
   :target: https://pypi.org/project/drclip/
