=========
Reference
=========


Commands
========
The `airship` shell command expects the path to `airship_home` as first
argument, then a sub-command which may have additional arguments. If
`airship` is called from the ``bin`` folder in `airship_home`, the first
argument is already provided by the bin/ script.


airship deploy
--------------
Run a full deployment: create new bucket, unpack tarball, install
dependencies, stop old process, start the new one, destroy old bucket.

Expects two arguments: a tarball (not gzipped) containing the
application, and the name of the process to deploy.

::

    $ bin/airship deploy myapp.tar web

airship run
-----------
Open a bash shell in the instance's folder. The ``prerun`` script, if
any, is executed as `rc` file. `run` accepts an optional argument, a
command to be run in the shell. With this option it behaves like ``bash
-c <command>``.

::

    $ bin/airship run web-jCCbfV 'echo "hello from instance in" `pwd`'

airship start
-------------
Start an instance. This simply configures the ``./server`` script,
inside the instance's folder, as a supervisor `program`.

::

    $ bin/airship start web-jCCbfV

airship stop
------------
Stops an instance. This simply removes the relevant `program` from
supervisor.

::

    $ bin/airship stop web-jCCbfV

airship destroy
---------------
Remove the instance (its folder and configuration files). Calls `stop`
first, in case the instance was running.

::

    $ bin/airship destroy web-jCCbfV

supervisord
-----------
Start the `supervisord` daemon. See `the supervisord documentation`_ for
details.

::

    $ bin/supervisord

.. _the supervisord documentation: http://supervisord.org/running.html#running-supervisord

supervisorctl
-------------
Interact with `supervisord`. Type `help` at the prompt to see what it
can do.

::

    $ bin/supervisorctl
