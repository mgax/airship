.. _tutorial-development:

Development
===========
You probably want to work on the application on your own computer, with
a local database, and running on a local port.  Sarge is for deployment,
but the same conventions used for Sarge can be used locally.


Virtualenv
----------
The application will most likely need dependencies (libraries) to run.
If you install them globally, at some point they will conflict with
dependencies of other projects.  Virtualenv_ creates a sandbox for each
project to install its libraries.  The rest of this tutorial assumes you
have created and activated a virtualenv.

.. _virtualenv: http://virtualenv.org/
