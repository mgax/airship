Running your code
=================


Process management
------------------
Sarge employs supervisord_ to start and manage bucket processes. This
means that a process must not daemonize. When starting a process, Sarge
looks for a file ``$BUCKET/Procfile``, in the same format as heroku_ and
foreman_, and runs the specified command, after setting up the
environment variables.

For local development you can use foreman_ or honcho_ and set
environment variables in the ``.env`` file.

.. _supervisord: http://supervisord.org/
.. _heroku: https://devcenter.heroku.com/articles/procfile#declaring-process-types
.. _foreman: http://ddollar.github.com/foreman/#PROCFILE
.. _honcho: http://pypi.python.org/pypi/honcho


Ports
-----
Each process is allocated a port number from the configured range. The
port number is found in the ``$PORT`` environment variable.

If the process needs to be accessible from the outside, e.g. from a
front-end web server or from another process in the same application,
then it needs a stable port number. Sarge takes care of this with the
help of haproxy_. Stable public ports are configured in ``sarge.yaml``
and proxied (at the TCP level) to the port of the running process.

.. _haproxy: http://haproxy.1wt.eu/


Logging
-------
A process should write log messages to its `stdout` or `stderr` file.
They are collected by `supervisord` and saved to
``$SARGE_HOME/var/log/$BUCKET_ID``.

Although `supervisord` has a limit on logfile size, it's a good idea to
rotate them using `logrotate`. Here is an example configuration::

    /var/local/myapp/var/log/*.log {
        missingok
        weekly
        rotate 4
        dateext
        delaycompress

        sharedscripts
        postrotate
            kill -USR2 `cat /var/local/myapp/var/run/supervisor.pid`
        endscript
    }

See also the `supervisord` `logging documentation`_.

.. _logging documentation: http://supervisord.org/logging.html
