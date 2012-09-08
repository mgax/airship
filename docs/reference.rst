=========
Reference
=========


Commands
========
The `sarge` shell command expects the path to `sarge_home` as first
argument, then a sub-command which may have additional arguments. If
`sarge` is called from the ``bin`` folder in `sarge_home`, the first
argument is already provided by the bin/ script.

sarge new
---------
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

sarge start
-----------
Start an instance. This simply configures the ``./server`` script,
inside the instance's folder, as a supervisor `program`.

sarge stop
----------
Stops an instance. This simply removes the relevant `program` from
supervisor.

sarge destroy
-------------
Remove the instance (its folder and configuration files). Calls `stop`
first, in case the instance was running.

supervisord
-----------
Start the `supervisord` daemon. See `the supervisord documentation`_ for
details.

.. _the supervisord documentation: http://supervisord.org/running.html#running-supervisord

supervisorctl
-------------
Interact with `supervisord`. Type `help` at the prompt to see what it
can do.
