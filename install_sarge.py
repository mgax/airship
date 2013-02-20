""" Sarge automated installation script
usage: python2.7 <(curl -fsSL raw.github.com/mgax/sarge/master/install_sarge.py) /var/local/my_awesome_app
"""

import os
import sys
import subprocess
import urllib
import json


SARGE_PACKAGE = 'https://github.com/mgax/sarge/tarball/master'
SARGE_GIT = 'git+https://github.com/mgax/sarge.git#egg=Sarge'
PATH_PY_URL = 'https://raw.github.com/jaraco/path.py/2.3/path.py'
VIRTUALENV_URL = 'https://raw.github.com/pypa/virtualenv/develop/virtualenv.py'
DISTRIBUTE_URL = ('http://pypi.python.org/packages/source/'
                  'd/distribute/distribute-0.6.32.tar.gz')
PIP_URL = 'https://github.com/qwcode/pip/tarball/53bbdf5'  # wheel_install branch
WHEEL_URL = ('http://pypi.python.org/packages/source/'
             'w/wheel/wheel-0.14.0.tar.gz')

SARGE_CFG_TEMPLATE = """\
python_dist: {python_dist}
python_interpreter: {python_interpreter}
port_range: {port_range}
port_map:
    web: 127.0.0.1:{web_port}
env:
"""


def filename(url):
    return url.split('/')[-1]


def install(sarge_home, python_bin, devel):
    username = os.popen('whoami').read().strip()
    virtualenv_path = sarge_home / 'opt' / 'airship-venv'
    virtualenv_bin = virtualenv_path / 'bin'
    sarge_cfg = sarge_home / 'etc' / 'airship.yaml'
    virtualenv_path.makedirs_p()

    if not (virtualenv_bin / 'python').isfile():
        import virtualenv
        print "creating virtualenv in {virtualenv_path} ...".format(**locals())
        virtualenv.create_environment(virtualenv_path,
                                      search_dirs=[sarge_home / 'dist'],
                                      use_distribute=True,
                                      never_download=True)
        subprocess.check_call([virtualenv_bin / 'pip', 'install',
                               sarge_home / 'dist' / filename(WHEEL_URL)])

    if devel:
        print "installing sarge in development mode ..."
        sarge_req = ['-e', SARGE_GIT]
    else:
        print "installing sarge ..."
        sarge_req = [SARGE_PACKAGE]
    subprocess.check_call([virtualenv_bin / 'pip', 'install'] + sarge_req)

    if not sarge_cfg.isfile():
        import random
        (sarge_home / 'etc').mkdir_p()
        base = random.randint(20, 600) * 100
        sarge_cfg.write_bytes(SARGE_CFG_TEMPLATE.format(
            python_dist=json.dumps(sarge_home / dist),
            port_range=json.dumps([base + 10, base + 99]),
            web_port=json.dumps(base),
            python_interpreter=json.dumps(sys.executable),
        ))
        subprocess.check_call([virtualenv_bin / 'airship', sarge_home, 'init'])

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


def download_to(url, parent_folder, fname=None):
    if fname is None:
        fname = filename(url)
    file_path = os.path.join(parent_folder, fname)
    if os.path.isfile(file_path):
        print "skipping {file_path}, already downloaded".format(**locals())
        return
    print "downloading {url} to {file_path}".format(**locals())
    http = urllib.urlopen(url)
    with open(file_path, 'wb') as f:
        f.write(http.read())
    http.close()


if __name__ == '__main__':
    sarge_home = os.path.abspath(sys.argv[1])
    dist = os.path.join(sarge_home, 'dist')
    if not os.path.isdir(dist):
        os.makedirs(dist)

    if len(sys.argv) > 2 and sys.argv[2] == '-e':
        devel = True
    else:
        devel = False

    download_to(PATH_PY_URL, dist)
    download_to(VIRTUALENV_URL, dist)
    download_to(DISTRIBUTE_URL, dist)
    download_to(PIP_URL, dist, 'pip-1.2.1.post1-2012-11-28.tar.gz')
    download_to(WHEEL_URL, dist)

    sys.path[0:0] = [dist]
    from path import path
    install(path(sarge_home), sys.executable, devel)
