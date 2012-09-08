=========
Reference
=========


Commands
========
The `sarge` shell command expects the path to `sarge_home` as first
argument, then a sub-command which may have additional arguments. If
`sarge` is called from the ``bin`` folder in `sarge_home`, the first
argument is already provided by the bin/ script.

new
---
Create a new application instance. Receives one argument, a JSON
document with information about the application; be sure to quote it
properly. The JSON may contain:

``application_name``
    Short string used to distinguish between application types. Good
    names are e.g. `web`, `worker`.

``prerun``
    Bash file to be sourced before running the application. This is
    the place to activate a virtualenv or set environment variables.

`new` prints the `id` of the new instance to `stderr`. Example::

    $ bin/sarge new '{"application_name": "web", "prerun": "sargerc"}'
    web-jCCbfV

start
-----
Start an instance. This simply configures the ``./server`` script,
inside the instance's folder, as a supervisor `program`.

stop
----
Stops an instance. This simply removes the relevant `program` from
supervisor.

destroy
-------
Remove the instance (its folder and configuration files). Calls `stop`
first, in case the instance was running.


API
===

:mod:`sarge.core`
-----------------
.. automodule:: sarge.core

.. autoclass:: Sarge
    :members:

.. autoclass:: Instance
    :members:


.. _plugins:

Plugins
-------

The main entry point for a plugin must be a one-argument callable. It
gets called at startup and passed in the :class:`~sarge.Sarge` instance.
At this point it can subscribe to Blinker events.

.. TODO how to activate a plugin


List of core plug-ins
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: sarge.nginx.NginxPlugin

.. autoclass:: sarge.core.VarFolderPlugin

.. autoclass:: sarge.core.ListenPlugin
