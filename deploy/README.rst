Example deployment
==================

The `fabfile.py` script in this folder contains two interesting
commands. **bootstrap** will set up a new sarge environment on a remote
server, assuming Python, `virtualenv` and `curl` are available.
**deploy** will install a demo application instance in the sarge
environment; run it repeatedly to see new instances being deployed,
replacing the old ones.
