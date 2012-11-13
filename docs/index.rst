Welcome to Sarge's documentation!
=================================

Sarge is a server-side tool, for deploying applications, inspired by the
`twelve-factor methodology`_. It's a wrapper around supervisor_,
virtualenv_, pip_ and haproxy_ which can install, start, monitor and
tear down successive versions of an application's process types.

.. _twelve-factor methodology: http://www.12factor.net/
.. _supervisor: http://supervisord.org/
.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://www.pip-installer.org/
.. _haproxy: http://haproxy.1wt.eu/


The source code is maintained on GitHub:
https://github.com/mgax/sarge.


Contents:

.. toctree::
   :maxdepth: 2

   usage
   environment
   running
   development
   reference
