import sys
import subprocess
from path import path


def set_up_virtualenv_and_requirements(airship, bucket, **extra):
    from airship.deployer import DeployError
    requirements_file = bucket.folder / 'requirements.txt'
    if requirements_file.isfile():
        config = airship.config.get('python', {})
        index_dir = config['dist']
        venv = bucket.folder / '_virtualenv'
        pip = venv / 'bin' / 'pip'
        virtualenv_py = airship.home_path / 'dist' / 'virtualenv.py'
        python = config.get('interpreter', 'python')

        try:
            subprocess.check_call([python, virtualenv_py, venv,
                                   '--distribute', '--never-download',
                                   '--extra-search-dir=' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to create a virtualenv.")

        try:
            subprocess.check_call([pip, 'install', 'wheel', '--no-index',
                                   '--find-links=file://' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to install wheel.")

        try:
            subprocess.check_call([pip, 'install', '-r', requirements_file,
                                   '--use-wheel', '--no-index',
                                   '--find-links=file://' + index_dir])
        except subprocess.CalledProcessError:
            raise DeployError(bucket, "Failed to install requirements.")


def activate_virtualenv(airship, bucket, environ, **extra):
    venv = bucket.folder / '_virtualenv'
    if venv.isdir():
        environ['PATH'] = ((venv / 'bin') + ':' + environ['PATH'])


def load(airship):
    from airship.deployer import bucket_setup
    from airship.core import bucket_run
    bucket_setup.connect(set_up_virtualenv_and_requirements, airship)
    bucket_run.connect(activate_virtualenv, airship)


def do_wheel(airship, args):
    config = airship.config.get('python', {})
    index_dir = config['dist']
    argv = [path(sys.prefix) / 'bin' / 'pip',
            'wheel',
            '--no-deps',
            '-w', index_dir]
    subprocess.check_call(argv + args.wheel_argv)


from airship.core import define_arguments


@define_arguments.connect
def register_wheel_subcommand(sender, create_command):
    import argparse
    wheel_cmd = create_command('wheel', do_wheel)
    wheel_cmd.add_argument('wheel_argv', nargs=argparse.REMAINDER)
