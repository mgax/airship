from mock import Mock, call, ANY
from common import SargeTestCase


class ProgramsRecorder(object):

    def __init__(self):
        self.programs = []

    def __call__(self, deployment_name, cfg_folder, programs):
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

    def test_start_instance_calls_restart_deployment(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        instance = sarge.new_instance()
        instance.start()
        self.assertEqual(sarge.daemons.restart_deployment.mock_calls,
                         [call(instance.id_)])

    def test_instance_has_one_program(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        sarge.daemons.configure_deployment = ProgramsRecorder()

        instance = sarge.new_instance()
        instance.start()

        self.assertEqual(sarge.daemons.configure_deployment.programs,
                         [{'name': instance.id_ + '_daemon', 'command': ANY}])

    def test_instance_program_command_is_called_run(self):
        sarge = self.sarge()
        sarge.daemons = Mock()
        sarge.daemons.configure_deployment = ProgramsRecorder()

        instance = sarge.new_instance()
        instance.start()

        self.assertEqual(sarge.daemons.configure_deployment.programs,
                         [{'name': ANY, 'command': 'run'}])

    def test_service_is_configured_at_instance_creation(self):
        sarge = self.sarge()
        instance = sarge.new_instance({'services': {
            'something': {'foo': 'bar'},
        }})

        services = instance.deployment.config['require-services']
        self.assertEqual(services['something'], {'foo': 'bar'})

    def test_two_instances_have_different_paths_and_ids(self):
        sarge = self.sarge()
        instance_1 = sarge.new_instance()
        instance_2 = sarge.new_instance()
        self.assertNotEqual(instance_1.folder, instance_2.folder)
        self.assertNotEqual(instance_1.id_, instance_2.id_)
