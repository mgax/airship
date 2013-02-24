from mock import Mock
from common import AirshipTestCase


class DeployErrorTest(AirshipTestCase):

    def setUp(self):
        from subprocess import CalledProcessError
        self.subprocess = self.patch('airship.contrib.python.subprocess')
        self.subprocess.CalledProcessError = CalledProcessError
        self.bucket = Mock(folder=self.tmp)
        self.bucket.airship.config = {'python': {'dist': self.tmp}}
        self.bucket.airship.home_path = self.tmp
        (self.tmp / 'requirements.txt').write_text("")

    def call_and_expect_failure(self):
        from airship.deployer import DeployError
        from airship.contrib.python import set_up_virtualenv_and_requirements
        with self.assertRaises(DeployError) as e:
            set_up_virtualenv_and_requirements(self.bucket)
        return e.exception

    def test_virtualenv_failure_raises_deploy_error(self):
        self.subprocess.check_call.side_effect = [
            self.subprocess.CalledProcessError(3, ''),
        ]
        err = self.call_and_expect_failure()
        self.assertEqual(err.message, "Failed to create a virtualenv.")
        self.assertIs(err.bucket, self.bucket)

    def test_pip_wheel_failure_raises_deploy_error(self):
        self.subprocess.check_call.side_effect = [
            None,
            self.subprocess.CalledProcessError(3, ''),
        ]
        err = self.call_and_expect_failure()
        self.assertEqual(err.message, "Failed to install wheel.")
        self.assertIs(err.bucket, self.bucket)

    def test_pip_requirements_failure_raises_deploy_error(self):
        self.subprocess.check_call.side_effect = [
            None,
            None,
            self.subprocess.CalledProcessError(3, ''),
        ]
        err = self.call_and_expect_failure()
        self.assertEqual(err.message, "Failed to install requirements.")
        self.assertIs(err.bucket, self.bucket)


class RunTest(AirshipTestCase):

    def test_run_activates_virtualenv(self):
        from run_test import mock_exec
        bucket = self.create_airship().new_bucket()
        venv = bucket.folder / '_virtualenv'
        venv.mkdir()
        with mock_exec() as calls:
            bucket.run('hello world')
        path_0 = calls[0].environ['PATH'].split(':')[0]
        self.assertEqual(path_0, venv / 'bin')
