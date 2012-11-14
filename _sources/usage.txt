Usage
=====


Bootstrapping
-------------
Before deploying any application we need to install `sarge` itself.
There is a handy script::

    $ python <(curl -fsSL raw.github.com/mgax/sarge/master/install_sarge.py) /var/local/my_awesome_app

Don't forget to start sarge's `supervisord` at boot, e.g. by adding the
following line to ``/etc/rc.local`` (replace `daemon` with the user
which should run the app)::

    su daemon -c '/var/local/my_awesome_app/bin/supervisord'


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
