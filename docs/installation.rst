Installation
============
Sarge is typically installed on a linux server with shell access.  It
runs on Python 2.6 or 2.7.  It also requires haproxy_ for port routing.

.. _haproxy: http://haproxy.1wt.eu/


Using the script
----------------
The `installer script`_ can install Sarge automatically.  Simply point
it to a directory (e.g. ``/var/local/my_awesome_app``) which needs to be
writable by the user running the script, or the user must have
permission to create it::

    $ python2.7 <(curl -fsSL raw.github.com/mgax/sarge/master/install_sarge.py) /var/local/my_awesome_app

If all goes well, the script will print a message, telling you about
``supervisord``.  This daemon controls processes of the deployed
application and it needs to run at all times.  You can start it by
calling ``/var/local/my_awesome_app/bin/supervisord`` manually.  It's a
good idea to configure your startup scripts (e.g. ``/etc/rc.local``) to
run this command, but make sure it runs with the correct user; the
installation message gives the right incantation.

.. _installer script: https://github.com/mgax/sarge/blob/master/install_sarge.py
