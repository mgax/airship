API
===

:mod:`sarge`
------------
.. automodule:: sarge

.. autoclass:: sarge.Sarge

    Instances provide a number of Blinker signals:

    `on_initialize`
        Triggered when a sarge home folder is created. `sender` is the
        :class:`~sarge.Sarge` instance.

    `on_activate_version`
        Triggered when a deployment is activated. `sender` is the
        :class:`~sarge.Deployment` instance. There is one keyword argument:
        `folder` - absolute path to new active version folder.

.. autoclass:: sarge.Deployment


Plugins
-------
The main entry point for a plugin must be a one-argument callable. It
gets called at startup and passed in the :class:`~sarge.Sarge` instance.
At this point it can subscribe to Blinker events.

.. TODO how to activate a plugin


List of core plug-ins
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: sarge.NginxPlugin
