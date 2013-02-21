Installation
============
Airship is typically installed on a linux server with shell access.  It
runs on Python 2.6 or 2.7.  It also requires haproxy_ for port routing.

.. _haproxy: http://haproxy.1wt.eu/


Using the script
----------------
The `installer script`_ can install Airship automatically.  Simply point
it to a directory (e.g. ``/var/local/my_awesome_app``) which needs to be
writable by the user running the script, or the user must have
permission to create it::

    $ python2.7 <(curl -fsSL raw.github.com/mgax/sarge/master/install_airship.py) /var/local/my_awesome_app

If all goes well, the script will print a message, telling you about
``supervisord``.  This daemon controls processes of the deployed
application and it needs to run at all times.  You can start it by
calling ``/var/local/my_awesome_app/bin/supervisord`` manually.  It's a
good idea to configure your startup scripts (e.g. ``/etc/rc.local``) to
run this command, but make sure it runs with the correct user; the
installation message gives the right incantation.

.. _installer script: https://github.com/mgax/sarge/blob/master/install_airship.py


Manually
--------
If you don't like magic scripts then you can install Airship by hand.

0. Choose a "home" folder.  This is where applications are deployed,
   configuration files live, and log files are written.  We'll call it
   ``$AIRSHIP_HOME`` below.
1. Create and activate a virtualenv.
2. Install airship and dependencies:
   ``pip install https://github.com/mgax/sarge/tarball/master``.
3. Create a configuration file in ``$AIRSHIP_HOME/etc/airship.yaml``.
   (**TODO**: describe what the configuration file should look like.)
4. Run ``airship $AIRSHIP_HOME init``. This creates some more files and
   folders in ``$AIRSHIP_HOME/etc``, a logfile folder in
   ``$AIRSHIP_HOME/var/log``, and convenience wrappers for some commands
   in ``$AIRSHIP_HOME/bin``.
5. Start ``$AIRSHIP_HOME/bin/supervisord`` and make sure it starts at
   system boot.
