import subprocess


def set_up_virtualenv_and_requirements(bucket, **extra):
    from airship.deployer import DeployError
    airship = bucket.airship
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


def load(airship):
    from airship.deployer import bucket_setup
    bucket_setup.connect(set_up_virtualenv_and_requirements)
