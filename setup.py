import sys
import distutils.core

dependencies = ['supervisor', 'blinker', 'path.py', 'PyYAML', 'kv']
if sys.version_info < (2, 7):
    dependencies += ['importlib', 'argparse']

distutils.core.setup(
    name='Airship',
    version='0.3-dev',
    packages=['airship', 'airship.contrib.python'],
    install_requires=dependencies,
    entry_points={
        'console_scripts': ['airship = airship.core:main'],
        'airship_plugins': ['python = airship.contrib.python:load'],
    },
)
