Useful patterns
===============


Log rotation
------------
Sarge writes log files to ``$SARGE_HOME/var/log/$BUCKET_ID``. Although
`supervisord` has a limit on logfile size, it's a good idea to rotate them
using `logrotate`. Here is an example configuration::

    /var/local/my_awesome_app/var/log/*.log {
        missingok
        weekly
        rotate 4
        dateext
        delaycompress

        sharedscripts
        postrotate
            kill -USR2 `cat /var/local/my_awesome_app/var/run/supervisor.pid`
        endscript
    }

See also the `supervisord` `logging documentation`_.

.. _logging documentation: http://supervisord.org/logging.html
