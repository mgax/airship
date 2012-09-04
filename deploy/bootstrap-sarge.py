""" Sarge automated installation script
usage: python <(curl -fsSL raw.github.com/alex-morega/sarge/master/deploy/bootstrap-sarge.py) path/to/sarge
"""

import os
import sys
import subprocess
import tempfile
import shutil
import urllib


SARGE_PACKAGE = 'https://github.com/alex-morega/sarge/tarball/master'

PATH_PY_URL = 'https://raw.github.com/jaraco/path.py/2.3/path.py'

VIRTUALENV_URL = 'https://raw.github.com/pypa/virtualenv/develop/virtualenv.py'

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

    sarge_home = path(sarge_home).abspath()
    if not sarge_home.exists():
        sarge_home.makedirs_p()

    username = os.popen('whoami').read().strip()
    virtualenv_path = sarge_home / 'var' / 'sarge-venv'
    virtualenv_bin = virtualenv_path / 'bin'
    sarge_cfg = sarge_home / 'etc' / 'sarge.yaml'

    if not (virtualenv_bin / 'python').isfile():
        import virtualenv
        print "creating virtualenv in {virtualenv_path} ...".format(**locals())
        virtualenv.create_environment(virtualenv_path, use_distribute=True)

    print "installing sarge ..."
    subprocess.check_call([virtualenv_bin / 'pip', 'install', SARGE_PACKAGE])

    if not sarge_cfg.isfile():
        (sarge_home / 'etc').mkdir_p()
        sarge_cfg.write_text('{"plugins": ["sarge:NginxPlugin"]}\n')
        subprocess.check_call([virtualenv_bin / 'sarge', sarge_home, 'init'])

    sarge_bin = sarge_home / 'bin'
    print "creating scripts in {sarge_bin}".format(**locals())
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


def download_to(url, file_path):
    print "downloading {url} to {file_path}".format(**locals())
    http = urllib.urlopen(url)
    with open(file_path, 'wb') as f:
        f.write(http.read())
    http.close()


if __name__ == '__main__':
    try:
        tmp = tempfile.mkdtemp()
        download_to(PATH_PY_URL, os.path.join(tmp, 'path.py'))
        download_to(VIRTUALENV_URL, os.path.join(tmp, 'virtualenv.py'))
        sys.path[0:0] = [tmp]
        install(sys.argv[1], sys.executable)
    finally:
        shutil.rmtree(tmp)
