from mock import Mock, patch
from common import SargeTestCase


class DeployTest(SargeTestCase):

    @patch('sarge.deployer.subprocess')
    def test_virtualenv_failure_raises_deploy_error(self, subprocess):
        from subprocess import CalledProcessError
        from sarge.deployer import (set_up_virtualenv_and_requirements,
                                    DeployError)
        subprocess.CalledProcessError = CalledProcessError
        subprocess.check_call.side_effect = CalledProcessError(3, '')
        (self.tmp / 'requirements.txt').write_text("")
        bucket = Mock(folder=self.tmp)
        bucket.sarge.config = {'wheel_index_dir': self.tmp}
        bucket.sarge.home_path = self.tmp
        with self.assertRaises(DeployError) as e:
            set_up_virtualenv_and_requirements(bucket)
        self.assertEqual(e.exception.message, "Failed to create a virtualenv.")
