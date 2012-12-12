Quickstart
==========
This page is a complete walkthrough of the process of deploying with
sarge. We're going to deploy a toy application that displays a "hello
web!" message on its homepage. It's built with Flask_ and the source is
at `github.com/mgax/sargeapp`_.

.. _github.com/mgax/sargeapp: https://github.com/mgax/sargeapp
.. _Flask: http://flask.pocoo.org/


Prepare the application for Sarge
---------------------------------
Applications running on Sarge need to follow some basic rules. Some are
inspired from the `12factor methodology`_, others are common practices when
writing Python applications.

.. _12factor methodology: http://www.12factor.net/

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

        web: python app.py runserver -dr -p $PORT

.. _its Procfile: https://github.com/mgax/sargeapp/blob/master/Procfile

**dependencies**
    It's customary to list your Python package dependencies in a
    ``requirements.txt`` file. With Sarge this becomes mandatory. The
    dependencies will be automatically installed in a fresh virtualenv_
    every time a new version of the app is deployed.

    ::

        Flask==0.9
        Jinja2==2.6
        Werkzeug==0.8.3

.. _virtualenv: http://www.virtualenv.org/

**persistence**
    The deployment folder is temporary; whenever a new version is
    deployed, this folder is deleted. Any data that needs to be saved
    from the application must be saved externally. Here are some
    examples:

    *database service*
        A specialised database (e.g. PostgreSQL). The application should
        read an environment variable to learn how to connect to the
        database.

    *web api*
        An API accessed via HTTP (e.g. Amazon S3). The service base URL
        and any API key or login information should be read from
        environment variables.

    *persistent folder*
        A folder on the server outside the deployment folder. The
        location is up to you, but it shoud be read by the application
        from an environment variable.


Local development
-----------------
All of the above constraints are intended to simplify deployment. But
you still need to run the code on the development machine. Luckily this
is easy, using honcho_ or foreman_. They read the ``Procfile`` and start
processes defined there, just like Sarge.

.. _honcho: https://github.com/nickstenning/honcho
.. _foreman: http://ddollar.github.com/foreman/

For local configuration, you can write environment variables in a file
named ``.env``, it will be loaded into the process environments. It's a
good idea to ignore this file from version control. Here is an ``.env``
file for our toy application::

    DEBUG=on
    MESSAGE=hello honcho!

To start the application locally simply run::

    honcho start

You can also run arbitrary commands, with the local configuration loaded
in the environment. For our toy app this command starts an interactive
shell::

    $ honcho run python app.py shell
    >>> import os
    >>> print os.environ['MESSAGE']
    hello honcho!


Set up Sarge on the server
--------------------------


Deploy with fabric
------------------
