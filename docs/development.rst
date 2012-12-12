Development
===========
To work on Sarge you will need additional libraries. Install them by
running ``pip install -r requirements-dev.txt``.


Unit tests
----------
Sarge has a suite of unit tests that exercise individual bits of the
implementation. They are located in the ``tests`` folder. Run them using
nose_::

    $ nosetests

.. _nose: https://nose.readthedocs.org/


Integration tests
-----------------

There is also a suite of integration tests which require a vagrant_
virtual machine::

    $ gem install vagrant
    $ vagrant box add precise64 http://files.vagrantup.com/precise64.box
    $ cd $SARGE_REPO/vagrant
    $ vagrant up

.. _vagrant: http://vagrantup.com/

Once the vagrant VM starts up, run the tests with nose. They are in the
``vagrant`` folder and not discovered by default, so they don't get
accidentally run as part of the unit test suite, therefore you must
invoke them explicitly::

    $ nosetests -sx vagrant
