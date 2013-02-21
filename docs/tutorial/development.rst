.. _tutorial-development:

Development
===========
You probably want to work on the application on your own computer, with
a local database, and running on a local port.  Airship is for
deployment, but the same conventions used for Airship can be used
locally.


Virtualenv
----------
The application will most likely need dependencies (libraries) to run.
If you install them globally, at some point they will conflict with
dependencies of other projects.  Virtualenv_ creates a sandbox for each
project to install its libraries.  The rest of this tutorial assumes you
have created and activated a virtualenv.

.. _virtualenv: http://virtualenv.org/


Install dependencies
--------------------
Each virtualenv comes with pip_ which we're going to use for installing
our application's dependencies::

    $ pip install -r requirements.txt

We also install the development tools which we're going to use a bit
later::

    $ pip install -r requirements-dev.txt

Whenever you add a dependency to the project, run ``pip freeze`` to get
a list of the libraries installed in the virtualenv, and update
``requirements.txt`` with the missing entries.

.. _pip: http://www.pip-installer.org/


Configure the application
-------------------------
The application receives configuration via environment variables, but
how do we set them?  For local development we create a file called
``.env``:

.. code-block:: bash

    DEBUG=on
    SECRET_KEY=asdf
    DATABASE=sqlite:///db.sqlite

This file will be picked up by Honcho when it runs our application.


Run with Honcho
---------------
Now we can finally run our application.  It's a simple command::

    $ honcho start

Honcho will read ``Procfile``, ``.env``, and run the command listed as
``web``, which starts a local server, on port 5000 by default.  Honcho
has a number of options, it can use different ports, or start more than
one process (or none at all) for each process type.

But how do we create our database table?  Remember that's a separate
command, ``syncdb``.  It needs the configuration because that's how it
knows where to find the database.  Luckily Honcho has us covered with
its ``run`` subcommand::

    $ honcho run python cloudlist.py syncdb

Everything after ``run`` is executed as a shell command, after setting
the environment variables from ``.env``.


Source control
--------------
Most likely you use a source control system for your project.  If not,
you should seriously consider using one.  For this tutorial we're going
to use git_.

.. _git: http://git-scm.com/


Not all files belong in the code repository.  Python bytecode files
(with the ``pyc`` extension) are generated when the code is run and
differ from one Python version to another.  My configuration is
different from yours so it makes no sense to commit ``.env``.  So the
repository should include a ``.gitignore`` file that contains at least
these lines::

    .env
    *.pyc

Dependencies also don't belong, they can be installed on each system
based on the requirements files. So if the virtualenv is inside the
project folder, be sure to create a ``.gitignore`` file inside it, with
the contents ``*``, which means "ignore all the files in this folder".
