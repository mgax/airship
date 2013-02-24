from common import AirshipTestCase


class DaemonErrorTest(AirshipTestCase):

    def test_supervisorctl_failure_raises_daemon_error(self):
        from airship.daemons import SupervisorError
        from subprocess import CalledProcessError
        subprocess = self.patch('airship.daemons.subprocess')
        subprocess.CalledProcessError = CalledProcessError
        subprocess.check_call.side_effect = CalledProcessError(3, '')
        airship = self.create_airship()
        bucket = airship.new_bucket()
        with self.assertRaises(SupervisorError):
            bucket.start()
