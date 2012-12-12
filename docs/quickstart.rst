Quickstart
==========
This page is a complete walkthrough of the process of deploying with
sarge. We're going to deploy a toy application that displays a "hello
web!" message on its homepage. It's built with Flask_ and the source is
at `github.com/mgax/sargeapp`_.

.. _github.com/mgax/sargeapp: https://github.com/mgax/sargeapp
.. _Flask: http://flask.pocoo.org/


Prepare the application for sarge
---------------------------------
Applications running on sarge need to follow some basic rules. Some are
inspired from the 12factor methodology, others are common practices when
writing Python applications.

.. _12factor: http://www.12factor.net/

**configuration**
    Any application needs some amount of configuration: database
    connections, email server, address to send error messages, etc. All
    of this information needs to come in via `environment variables`_.
    In Python they can be read from `os.environ`_ or by using the env_
    library.

    ::

        import os
        from peewee import SqliteDatabase
        db = SqliteDatabase(os.environ['DATABASE'])

.. _environment variables: https://en.wikipedia.org/wiki/Environment_variable
.. _os.environ: http://docs.python.org/library/os#os.environ
.. _env: http://pypi.python.org/pypi/env

**process types**
    Unless you plan to serve static webpages, the application needs to
    run as one or more processes. For example, a `web` process type
    handles incoming HTTP requests, and a `worker` process type handles
    queued jobs. Process types are listed in a file named ``Procfile``
    at the root of the repository. For each process type we provide the
    shell command to start the process.

    Our example application defines, in `its Procfile`_, a single
    process type named `web`. Its shell command includes the ``$PORT``
    variable. This is set by Sarge, and it's the port number that our
    process should listen on. Sarge will route incoming HTTP requests to
    this port.

    ::

        web: ./app.py $PORT

.. _its Procfile: https://github.com/mgax/sargeapp/blob/master/Procfile


Set up sarge on the server
--------------------------


Deploy with fabric
------------------
