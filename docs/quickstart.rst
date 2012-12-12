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

.. _environment variables: https://en.wikipedia.org/wiki/Environment_variable
.. _os.environ: http://docs.python.org/library/os#os.environ
.. _env: http://pypi.python.org/pypi/env


Set up sarge on the server
--------------------------


Deploy with fabric
------------------
