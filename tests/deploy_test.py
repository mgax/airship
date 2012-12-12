from mock import Mock, patch
from common import SargeTestCase


class DeployErrorTest(SargeTestCase):

    def setUp(self):
        from subprocess import CalledProcessError
        self.subprocess = self.patch('sarge.deployer.subprocess')
        self.subprocess.CalledProcessError = CalledProcessError
        self.bucket = Mock(folder=self.tmp)
        self.bucket.sarge.config = {'python_dist': self.tmp}
        self.bucket.sarge.home_path = self.tmp
        (self.tmp / 'requirements.txt').write_text("")

    def call_and_expect_failure(self):
        from sarge.deployer import (set_up_virtualenv_and_requirements,
                                    DeployError)
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


class DaemonErrorTest(SargeTestCase):

    def test_supervisorctl_failure_raises_daemon_error(self):
        from sarge.daemons import SupervisorError
        from subprocess import CalledProcessError
        subprocess = self.patch('sarge.daemons.subprocess')
        subprocess.CalledProcessError = CalledProcessError
        subprocess.check_call.side_effect = CalledProcessError(3, '')
        sarge = self.create_sarge()
        bucket = sarge.new_bucket()
        with self.assertRaises(SupervisorError) as err:
            bucket.start()
