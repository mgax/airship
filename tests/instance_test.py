from mock import Mock, patch, call, ANY
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

    def test_get_instance_with_invalid_name_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.sarge().get_instance('nonesuch')

    def test_start_instance_calls_restart_instance(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        instance = sarge.new_instance()
        instance.start()
        self.assertEqual(sarge.daemons.start_instance.mock_calls,
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
