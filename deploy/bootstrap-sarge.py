import os
import sys
import subprocess


SARGE_PACKAGE = 'https://github.com/alex-morega/sarge/tarball/master'

SARGE_SCRIPT = """#!/bin/bash
'{virtualenv_bin}/sarge' '{sarge_home}' "$@"
"""

SUPERVISORD_SCRIPT = """#!/bin/bash
'{virtualenv_bin}/supervisord' -c '{sarge_home}/etc/supervisor.conf'
"""

SUPERVISORCTL_SCRIPT = """#!/bin/bash
'{virtualenv_bin}/supervisorctl' -c '{sarge_home}/etc/supervisor.conf' $@
"""


def install(sarge_home, python_bin):
    from path import path
    username = os.popen('whoami').read().strip()
    virtualenv_path = sarge_home / 'var' / 'sarge-venv'
    virtualenv_bin = virtualenv_path / 'bin'
    sarge_cfg = sarge_home / 'etc' / 'sarge.yaml'

    if not (virtualenv_bin / 'python').isfile():
        virtualenv_path.makedirs_p()
        subprocess.check_call(['virtualenv', virtualenv_path,
                               '-p', python_bin, '--distribute'])

    subprocess.check_call([virtualenv_bin / 'pip', 'install', SARGE_PACKAGE])

    if not sarge_cfg.isfile():
        (sarge_home / 'etc').mkdir_p()
        sarge_cfg.write_text('{"plugins": ["sarge:NginxPlugin"]}\n')
        subprocess.check_call([virtualenv_bin / 'sarge', sarge_home, 'init'])

    sarge_bin = sarge_home / 'bin'
    sarge_bin.makedirs_p()

    with open(sarge_bin / 'sarge', 'wb') as f:
        f.write(SARGE_SCRIPT.format(**locals()))
        path(f.name).chmod(0755)

    with open(sarge_bin / 'supervisord', 'wb') as f:
        f.write(SUPERVISORD_SCRIPT.format(**locals()))
        path(f.name).chmod(0755)

    with open(sarge_bin / 'supervisorctl', 'wb') as f:
        f.write(SUPERVISORCTL_SCRIPT.format(**locals()))
        path(f.name).chmod(0755)

    cmd = "{sarge_home}/bin/supervisord".format(**locals())
    fullcmd = "su {username} -c '{cmd}'".format(**locals())

    print
    print ("Installation complete! Run the following command "
           "on system startup:\n")
    print "  " + fullcmd
    print
    print "To start supervisord now, run this:"
    print
    print "  " + cmd
    print

if __name__ == '__main__':
    try:
        from path import path
    except ImportError:
        print "This script requires the path.py library:"
        print
        print "  curl -O 'https://raw.github.com/jaraco/path.py/2.3/path.py'"
        print
    else:
        install(path(os.getcwd()), sys.executable)
