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


Deploying an instance
---------------------
A sarge home folder is a container of application instances. Any number
of them can be created, started, stopped and destroyed. Instances have
an `application_name` property which makes it easy to distinguish
between application types (e.g. web server, background worker).

First we create an instance::

    $ bin/sarge new '{"application_name": "web"}'
    web-jCCbfV

The `new` command printed the instance's `id`, ``web-jCCbfV``. It also
created an instance folder with the same name. This is where we need to
deploy our application code. Sarge expects an executable named
``server`` in the instance folder::

    $ cat > web-jCCbfV/server <<EOF
    #!/usr/bin/env python
    from wsgiref.simple_server import make_server, demo_app
    httpd = make_server('', 8000, demo_app)
    print "Serving on port 8000..."
    httpd.serve_forever()
    EOF
    $ chmod +x web-jCCbfV/server

Now we can `start`, `stop` and `destroy` the instance.
