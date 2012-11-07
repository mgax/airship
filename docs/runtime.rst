The runtime environment
=======================
When code runs under `sarge` it can expect certain conventions about its
environment.


App configuration variables
---------------------------
An application receives its configuration via environment variables.
These can be database connection URIs, session secrets, path to a
persistent folder, etc.

Sarge loads configuration variables from ``etc/app/config.json`` which
should contain a dictionary with string values::

    {
        "SENTRY_DSN": "http://<key>@localhost/2",
        "DATA_PATH": "/var/local/myapp/var/db",
        "ELASTICSEARCH_URL": "http://localhost:21058"
    }


Virtualenv and dependencies
---------------------------
Sarge can install dependencies for Python packages if the application
archive contains a top-level ``requirements.txt`` file. The deployment
command creates a virtualenv_ named ``$BUCKET/_virtualenv`` and installs
the requirements using pip_.

All required packages must be available in ``$SARGE_HOME/dist`` because,
in the interest of speed, `pip` doesn't look in PyPI. Consider providing
wheel_ packages for even faster installation.

At runtime, ``$BUCKET/_virtualenv/bin`` is prepended to ``$PATH``, which
effectively activates the virtualenv.

.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://www.pip-installer.org/
.. _wheel: http://wheel.readthedocs.org/
