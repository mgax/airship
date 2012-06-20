Tutorial
========

This step-by-step guide assumes you want to deploy applications on a
Debian or Ubuntu server. You need a shell account with sudo privileges.


Installation
------------
Sarge needs Python 2.6 or 2.7. You also need virtualenv_ and a compiler.

.. _virtualenv: http://www.virtualenv.org/

::

    sudo apt-get install python2.6 python-virtualenv nginx
    sudo apt-get install build-essential python2.6-dev libyaml-dev

Let's set up the sarge home in ``/var/local/sarge``. Say you're logged
in as `joe`. Create the folder and fetch the source code::

    sudo mkdir /var/local/sarge-home
    sudo chown joe: /var/local/sarge-home
    cd /var/local/sarge-home

Set up a virtual environment and install sarge::

    virtualenv .
    bin/pip install https://github.com/alex-morega/sarge/zipball/master

Initialize sarge::

    sudo bin/sarge init
    sudo bin/supervisord


The first deployment
--------------------
Each application installed with sarge needs its own `deployment`. Think
of a deployment as an application container, configured to provide
whatever resources (e.g. database, temporary folder) the application
needs.

Let's create a deployment for our application. It's just a configuration
file specifying a name and unix user::

    cat > deployments/demo.yaml <<EOF
    {
        "name": "demo",
        "user": "joe",
        "nginx_options": {
            "listen": "8013"
        }
    }
    EOF

Before deploying we need to ask sarge to prepare a new version of our
deployment::

    sudo bin/sarge . new_version demo

The `new_version` command should print the absolute path of a newly
created folder and it's probably ``/var/local/sarge-home/demo/1``.
That's where we're supposed to write our application. We'll just write
an application configuration file with the urlmap and nginx port, and
use the `demo application from wsgiref`_::

    cat > demo/1/sargeapp.yaml <<EOF
    {
        "url_cfg": {
            "type": "wsgi",
            "url": "/",
            "wsgi_app": "wsgiref.simple_server:demo_app"
        }
    }
    EOF

.. _`demo application from wsgiref`: http://docs.python.org/library/wsgiref#wsgiref.simple_server.demo_app

Now it's time to activate the version. This tells sarge to set up
`nginx` and `supervisor` and then starts up the application::

    sudo bin/sarge . activate_version demo demo/1

To make sure the application is working, access the homepage using
`cURL`::

    curl http://localhost:8013/


More examples
-------------
For working examples of deployments, see ``vagrant/deployment_test.py``
in the sarge source code repository. Those are automated tests that
deploy against a local virtual machine.
