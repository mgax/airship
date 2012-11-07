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
