from datetime import datetime
import json
from mock import Mock, patch, call
from common import SargeTestCase


class ProgramsRecorder(object):

    def __init__(self):
        self.programs = []

    def __call__(self, instance_id, programs):
        self.programs.extend([{'name': name, 'command': p['command']}
                              for name, p in programs])


class InstanceTest(SargeTestCase):

    def test_new_instance_creates_instance_folder(self):
        sarge = self.sarge()
        instance = sarge.new_instance()
        self.assertTrue(instance.folder.isdir())

    def test_get_instance_returns_instance_with_correct_folder(self):
        sarge = self.sarge()
        instance = sarge.new_instance()
        same_instance = sarge.get_instance(instance.id_)
        self.assertEqual(instance.folder, same_instance.folder)

    def test_get_instance_with_app_name_returns_instance(self):
        sarge = self.sarge()
        instance = sarge.new_instance({'application_name': 'jack'})
        same_instance = sarge.get_instance('jack')
        self.assertEqual(instance.folder, same_instance.folder)

    def test_get_instance_with_invalid_name_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.sarge().get_instance('nonesuch')

    def test_new_instance_configures_daemon_to_stopped(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        instance = sarge.new_instance()
        self.assertEqual(sarge.daemons.configure_instance_stopped.mock_calls,
                         [call(instance)])

    def test_start_instance_configures_daemon_to_running(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        instance = sarge.new_instance()
        instance.start()
        self.assertEqual(sarge.daemons.configure_instance_running.mock_calls,
                         [call(instance)])

    def test_trigger_instance_calls_daemon_start(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        instance = sarge.new_instance()
        instance.trigger()
        self.assertEqual(sarge.daemons.trigger_instance.mock_calls,
                         [call(instance)])

    def test_service_is_configured_at_instance_creation(self):
        sarge = self.sarge()
        instance = sarge.new_instance({'services': {
            'something': {'foo': 'bar'},
        }})

        services = instance.config['require-services']
        self.assertEqual(services['something'], {'foo': 'bar'})

    def test_two_instances_have_different_paths_and_ids(self):
        sarge = self.sarge()
        instance_1 = sarge.new_instance()
        instance_2 = sarge.new_instance()
        self.assertNotEqual(instance_1.folder, instance_2.folder)
        self.assertNotEqual(instance_1.id_, instance_2.id_)

    def test_unlucky_instance_id_generator_gives_up(self):
        sarge = self.sarge()
        with patch('sarge.core.random') as random:
            random.choice.return_value = 'z'
            sarge.new_instance()
            with self.assertRaises(RuntimeError):
                sarge.new_instance()

    def test_instance_metadata_contains_creation_time(self):
        sarge = self.sarge()
        t0 = datetime.utcnow().isoformat()
        instance = sarge.new_instance()
        t1 = datetime.utcnow().isoformat()
        creation = instance.meta['CREATION_TIME']
        self.assertTrue(t0 <= creation <= t1)

    def test_instance_metadata_contains_app_name(self):
        sarge = self.sarge()
        instance = sarge.new_instance({'application_name': 'testy'})
        self.assertEqual(instance.meta['APPLICATION_NAME'], 'testy')

    def test_instance_id_starts_with_app_name(self):
        sarge = self.sarge()
        instance = sarge.new_instance({'application_name': 'testy'})
        self.assertTrue(instance.id_.startswith('testy-'))


class InstanceListingTest(SargeTestCase):

    def test_listing_with_no_instances_returns_empty_list(self):
        sarge = self.sarge()
        report = sarge.list_instances()
        self.assertEqual(report['instances'], [])

    def test_listing_with_two_instances_contains_their_ids(self):
        sarge = self.sarge()
        instance_1 = sarge.new_instance()
        instance_2 = sarge.new_instance()
        report = sarge.list_instances()
        self.assertItemsEqual([i['id'] for i in report['instances']],
                              [instance_1.id_, instance_2.id_])

    def test_listing_contains_metadata(self):
        sarge = self.sarge()
        sarge.new_instance({'application_name': 'testy'})
        report = sarge.list_instances()
        [instance_data] = report['instances']
        self.assertEqual(instance_data['meta']['APPLICATION_NAME'], 'testy')


class InstanceConfigTest(SargeTestCase):

    def test_run_prepares_environ_from_etc_app_config(self):
        os = self.patch('sarge.core.os')
        os.environ = {}
        (self.tmp / 'etc' / 'app').mkdir_p()
        with (self.tmp / 'etc' / 'app' / 'config.json').open('wb') as f:
            json.dump({'SOME_CONFIG_VALUE': "hello there!"}, f)
        sarge = self.sarge()
        sarge.new_instance().run(None)
        [execve_call] = os.execve.mock_calls
        environ = execve_call[1][2]
        self.assertEqual(environ['SOME_CONFIG_VALUE'], "hello there!")
