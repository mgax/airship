from fabric.api import env, run
from path import path


def setUpModule():
    env['key_filename'] = path(__file__).parent/'vagrant_id_rsa'
    env['host_string'] = 'vagrant@192.168.13.13'


def tearDownModule():
    from fabric.network import disconnect_all
    disconnect_all()


def test_ping():
    assert run('pwd') == '/home/vagrant'
