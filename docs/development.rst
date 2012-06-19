Development
===========

To work on Sarge you will need additional libraries. Install them by
running ``pip install -r requirements-dev.txt``.

Automated tests
---------------

Unit tests are located in the ``tests`` folder. They can be run simply
by calling `nosetests`.

There is also a suite of integration tests which require a vagrant_
virtual machine::

    $ gem install vagrant
    $ vagrant box add lucid32 http://files.vagrantup.com/lucid32.box
    $ cd $SARGE_REPO/vagrant
    $ vagrant up

.. _vagrant: http://vagrantup.com/

Once the vagrant VM starts up, run the tests with nose. They are in the
``vagrant`` folder and not discovered by default, so they don't get
accidentally run as part of the unit test suite, therefore you must
invoke them explicitly::

    $ nosetests vagrant
