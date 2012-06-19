Philosophy
==========

Sarge lives on the server and performs deployments. It's responsible for
setting up folders, creating databases, configuring web servers.

For now Sarge is hardcoded to use supervisor_ for managing subprocesses
and nginx_ as front-end web sever. Any other tasks should be handled by
:ref:`plugins`.

.. _supervisor: http://supervisord.org/
.. _nginx: http://www.nginx.org/


Hosting configuration
---------------------
Sarge typically runs as the root user because it needs to execute
sysadmin tasks.

For each deployment there is a configuration file describing the
deployment's name, effective unix user, and services available. This
part is not left up to the application; it should be explicitly
described separately. This allows us to prepare, for example, a staging
and production environment with different configurations, or shared
database among several applications, without hardcoding any paths or
names in the application's source code.


Hosted application
------------------
From an application's point of view, sarge provides configuration
information, such as paths and database connection URIs. The application
just needs to define a URL map describing its "entry points".

Fabric_ can help with automated deployment. A `fabfile` can call ``sarge
new_version``, upload the application, then call ``sarge
activate_version``.

.. _fabric: http://fabfile.org/
