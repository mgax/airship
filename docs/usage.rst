Usage
=====


Bootstrapping
-------------
Sarge code runs on the server, so whenever we deploy to a new host, we
first need to install sarge itself. ``pip install`` shoud be enough to
install the package, and it's a good idea to do this in a virtualenv_.

Then we need to choose a home folder for the deployment. This is where
instances and configuration files will be created. If the application is
called `gardensale` we could run ``sarge /var/local/gardensale init``.
This will create an ``etc`` folder (for configuration files), a ``var``
folder (for logs, pidfiles, sockets, etc), and a ``bin`` folder, with
convenient shortcuts to the `sarge`, `supervisord` and `supervisorctl`
commands.

The whole bootstrapping process can be automated with `this script`_
that creates a virtualenv, installs sarge, and initializes a home folder::

    $ python <(curl -fsSL raw.github.com/mgax/sarge/master/deploy/bootstrap-sarge.py) /var/local/gardensale

.. _virtualenv: http://www.virtualenv.org/
.. _`this script`: https://github.com/mgax/sarge/blob/master/deploy/bootstrap-sarge.py
