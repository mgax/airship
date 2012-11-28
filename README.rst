Sarge: deployment made easy
===========================

Deployment doesn't have to be hard. Eliminate manual installation steps
and arcane fabfiles. Sarge provides a consistent environment for your
app to run in production.

* A virtualenv_ for each new version.
* Dependencies get installed cf. ``requirements.txt``, using wheels_ if
  available.
* `stdout` and `stderr` are redirected to a log file.
* Inject configuration via `environment variables`_.
* Better `dev/prod parity`_, run locally with Foreman_ or Honcho_.

.. _virtualenv: http://www.virtualenv.org/
.. _wheels: http://wheel.readthedocs.org/
.. _environment variables: http://www.12factor.net/config
.. _dev/prod parity: http://www.12factor.net/dev-prod-parity
.. _foreman: http://ddollar.github.com/foreman/
.. _honcho: https://github.com/nickstenning/honcho
