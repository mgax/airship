.. _tutorial:

Tutorial
========

This step-by-step guide assumes you want to deploy applications on a
Debian or Ubuntu server. You need a shell account with sudo privileges.


Installation
------------
Sarge runs on Python 2.6 or 2.7. You also need virtualenv_ and a
compiler.

.. _virtualenv: http://www.virtualenv.org/

::

    sudo apt-get install python2.6 python-virtualenv nginx
    sudo apt-get install build-essential python2.6-dev libyaml-dev

Let's set up the sarge home in ``/var/local/awesome``, with a
virtualenv in ``/var/local/awesome/var/sarge-venv``::

    sudo mkdir /var/local/awesome
    sudo chown `whoami`: /var/local/awesome
    cd /var/local/awesome
    mkdir -p var/sarge-venv
    virtualenv var/sarge-venv
    var/sarge-venv/bin/pip install https://github.com/alex-morega/Sarge/zipball/master

Configure and initialize sarge::

    mkdir etc
    echo '{"plugins": ["sarge:NginxPlugin", "sarge:VarFolderPlugin"]}' > etc/sarge.yaml
    sudo var/sarge-venv/bin/sarge . init

Start up supervisor::

    var/sarge-venv/bin/supervisord -c etc/supervisor.conf


Deploying the first instance
----------------------------
Every time we deploy an application to sarge, we first create a new
`instance`. The instance is a container: a folder for the application
itself, a configuration file, and services set up.

Let's start up an instance with a simple configuration. The `new`
command creates an instance with a random ID and prints that to the
console. We must provide a JSON configuration string as argument::

    $ var/sarge-venv/bin/sarge . new '{
        "application_name": "webapp",
        "services": {"storage": {"type": "persistent-folder"}}}'
    Jh3KH6

In the newly created folder we need to create an executable named
``server``. This is our application, and we'll use the `wsgiref`
demo server::

    $ cat > Jh3KH6/server <<EOF
    #!/usr/bin/env python
    from wsgiref.simple_server import make_server, demo_app
    httpd = make_server('', 8000, demo_app)
    print "Serving on port 8000..."
    httpd.serve_forever()
    EOF
    $ chmod +x Jh3KH6/server

Now we just need to start it up::

    $ var/sarge-venv/bin/sarge . start Jh3KH6


To make sure the application is working, we can access the homepage
using `cURL`::

    curl http://localhost:8000/


More examples
-------------
For working examples of deployments, see `vagrant/deployment_test.py`_
in the sarge source code repository. Those are automated tests that
deploy against a local virtual machine.

.. _`vagrant/deployment_test.py`: https://github.com/alex-morega/sarge/blob/master/vagrant/deployment_test.py
