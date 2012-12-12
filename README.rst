Sarge: deployment made easy
===========================

Deployment doesn't have to be hard. Eliminate manual installation steps
and arcane fabfiles. Sarge provides a consistent environment for your
app to run in production.

* A virtualenv_ for each new version.
* Dependencies get installed cf. ``requirements.txt``, using wheels_ if
  available.
* Configure process types in a Procfile_ and they get started automatically.
* `stdout` and `stderr` are redirected to a log file.
* Inject configuration via `environment variables`_.
* Better `dev/prod parity`_, run locally with Foreman_ or Honcho_.

.. _virtualenv: http://www.virtualenv.org/
.. _wheels: http://wheel.readthedocs.org/
.. _procfile: http://ddollar.github.com/foreman/#PROCFILE
.. _environment variables: http://www.12factor.net/config
.. _dev/prod parity: http://www.12factor.net/dev-prod-parity
.. _foreman: http://ddollar.github.com/foreman/
.. _honcho: https://github.com/nickstenning/honcho


See the Quickstart_ to get a feel for the deployment process.

.. _Quickstart: https://sarge-deployer.readthedocs.org/en/latest/quickstart.html

You can use `this fabfile`_ in your project to deploy against a Sarge
server. To set up the server quickly, run this command::

    python2.7 <(curl -fsSL raw.github.com/mgax/sarge/master/install_sarge.py) /var/local/my_awesome_app

.. _this fabfile: https://gist.github.com/4266737
