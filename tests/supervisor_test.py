import sys
import ConfigParser
from path import path
from mock import call, ANY
from common import AirshipTestCase


def read_config(cfg_path):
    config = ConfigParser.RawConfigParser()
    config.read([cfg_path])
    return config


MISSING = object()


def config_file_checker(cfg_path):
    config = read_config(cfg_path)

    def eq_config(section, field, ok_value):
        try:
            cfg_value = config.get(section, field)
        except ConfigParser.NoOptionError:
            cfg_value = MISSING
        msg = 'Configuration field [%s] %s\n%r != %r' % (
            section, field, cfg_value, ok_value)
        assert cfg_value == ok_value, msg

    return eq_config


class SupervisorConfigurationTest(AirshipTestCase):

    def setUp(self):
        self.mock_supervisorctl = self.patch('airship.daemons.Supervisor.ctl')

    def test_generate_supervisord_cfg_with_no_deployments(self):
        self.create_airship().generate_supervisord_configuration()

        config_path = self.tmp / 'etc' / 'supervisor.conf'
        eq_config = config_file_checker(config_path)

        eq_config('unix_http_server', 'file',
                  self.tmp / 'var' / 'run' / 'supervisor.sock')
        eq_config('rpcinterface:supervisor', 'supervisor.rpcinterface_factory',
                  'supervisor.rpcinterface:make_main_rpcinterface')
        eq_config('supervisord', 'logfile',
                  self.tmp / 'var' / 'log' / 'supervisor.log')
        eq_config('supervisord', 'pidfile',
                  self.tmp / 'var' / 'run' / 'supervisor.pid')
        eq_config('supervisord', 'directory', self.tmp)
        eq_config('supervisorctl', 'serverurl',
                  'unix://' + self.tmp / 'var' / 'run' / 'supervisor.sock')
        eq_config('include', 'files', self.tmp / 'etc/supervisor.d/*')

    def bucket_cfg(self, bucket):
        return self.tmp / 'etc' / 'supervisor.d' / bucket.id_

    def test_generate_supervisord_cfg_with_run_command(self):
        bucket = self.create_airship().new_bucket()
        (bucket.folder / 'Procfile').write_text(
            'one: run this command on $PORT\n'
            'two: and $THIS other one\n'
        )
        bucket._read_procfile()
        bucket.start()

        eq_config = config_file_checker(self.bucket_cfg(bucket))
        section = 'program:%s-one' % bucket.id_

        eq_config(section, 'command',
                  'bin/airship run -d {0} one'.format(bucket.id_))
        eq_config(section, 'redirect_stderr', 'true')
        eq_config(section, 'stdout_logfile',
                  self.tmp / 'var' / 'log' / 'one.log')
        eq_config(section, 'startretries', '1')

    def test_bucket_start_changes_autostart_to_true(self):
        bucket = self.create_airship().new_bucket()
        (bucket.folder / 'Procfile').write_text('web: ./runweb $PORT\n')
        bucket._read_procfile()
        bucket.start()

        section = 'program:%s-web' % bucket.id_
        eq_config = config_file_checker(self.bucket_cfg(bucket))
        eq_config(section, 'autostart', 'true')
        eq_config(section, 'startsecs', '2')

    def test_bucket_stop_changes_autostart_to_false(self):
        bucket = self.create_airship().new_bucket()
        bucket.start()
        (bucket.folder / 'Procfile').write_text('web: ./runweb $PORT\n')
        bucket._read_procfile()
        bucket.stop()

        section = 'program:%s-web' % bucket.id_
        eq_config = config_file_checker(self.bucket_cfg(bucket))
        eq_config(section, 'autostart', 'false')
        eq_config(section, 'startsecs', '0')

    def test_bucket_start_triggers_supervisord_update(self):
        bucket = self.create_airship().new_bucket()
        self.mock_supervisorctl.reset_mock()
        bucket.start()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_bucket_stop_triggers_supervisord_update(self):
        bucket = self.create_airship().new_bucket()
        bucket.start()
        self.mock_supervisorctl.reset_mock()
        bucket.stop()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_bucket_destroy_triggers_supervisord_update(self):
        bucket = self.create_airship().new_bucket()
        bucket.start()
        bucket.stop()
        self.mock_supervisorctl.reset_mock()
        bucket.destroy()
        self.assertEqual(self.mock_supervisorctl.mock_calls,
                         [call(['update'])])

    def test_destroy_bucket_removes_its_supervisor_configuration(self):
        bucket = self.create_airship().new_bucket()
        bucket.start()
        cfg_path = self.tmp / 'etc' / 'supervisor.d' / bucket.id_
        self.assertTrue(cfg_path.isfile())
        bucket.destroy()
        self.assertFalse(cfg_path.isfile())


class SupervisorInvocationTest(AirshipTestCase):

    def test_invoke_supervisorctl(self):
        self.mock_subprocess.reset_mock()
        self.create_airship().daemons.ctl(['hello', 'world!'])
        supervisorctl_path = (path(sys.prefix).abspath() /
                              'bin' / 'supervisorctl')
        cfg_path = self.tmp / 'etc' / 'supervisor.conf'
        self.assertEqual(self.mock_subprocess.check_call.mock_calls,
                         [call([supervisorctl_path,
                                '-c', cfg_path,
                                'hello', 'world!'], stdout=ANY)])
