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

supervisord
~~~~~~~~~~~
Sarge relies on supervisord to keep track of running instances. After
deployment, you should start the supervisord process, by calling
``bin/supervisord`` from the sarge home folder. It should also be called
at system boot, e.g. from ``/etc/rc.local``; be sure to run it as the
correct user, which is probably not `root`.

loging
~~~~~~
Instance logs are handled by `supervisord`. They are saved in the sarge
home folder, as ``var/log/${INSTANCE_ID}.log``.

You can either let `supervisord` rotate logs itself, based on the log
file size, or the system-wide `logrotate` utility. If you choose
`logrotate` don't forget to tell `supervisord` to re-open its logs::

    $ kill -USR2 `cat /var/local/gardensale/var/run/supervisord.pid`

See the `supervisord` `logging documentation`_ for details.

.. _logging documentation: http://supervisord.org/logging.html


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


Rolling deployment
------------------
Sarge can host any number of instances, even if the application name is
the same. This allows us to perform a rolling deployment:

* Create a new instance of the application.
* Install the current version of source code in that instance.
* Start up the instance.
* Run some kind of checks to see if the site is sane.
* Configure the front-end web server to point to the new instance.
* Tear down the old instance.

If the sanity checks fail, we simply abort, and tear down the new
instance.
