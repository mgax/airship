Welcome to Sarge's documentation!
=================================

Sarge is a server-side tool for deploying applications inspired by the
`twelve-factor methodology`_. It's a wrapper around supervisor_, with
logic to set up and tear down application instances, and plugins to
configure services for each instance (e.g. persistence). Take a look at
the `example deployment scripts`_ to get a feel for the deployment process.

.. _twelve-factor methodology: http://www.12factor.net/
.. _supervisor: http://supervisord.org/
.. _example deployment scripts: https://github.com/mgax/sarge/tree/master/deploy


The source code is maintained on GitHub:
https://github.com/mgax/Sarge.


Contents:

.. toctree::
   :maxdepth: 2

   usage
   environment
   development
   reference
