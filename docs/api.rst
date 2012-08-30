API
===


:mod:`sarge.core`
-----------------
.. automodule:: sarge.core

.. autoclass:: Sarge
    :members:

.. autoclass:: Instance
    :members:


.. _plugins:

Plugins
-------

The main entry point for a plugin must be a one-argument callable. It
gets called at startup and passed in the :class:`~sarge.Sarge` instance.
At this point it can subscribe to Blinker events.

.. TODO how to activate a plugin


List of core plug-ins
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: sarge.nginx.NginxPlugin

.. autoclass:: sarge.core.VarFolderPlugin

.. autoclass:: sarge.core.ListenPlugin
