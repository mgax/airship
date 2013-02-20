import sys
import distutils.core

dependencies = ['supervisor', 'blinker', 'path.py', 'PyYAML', 'kv']
if sys.version_info < (2, 7):
    dependencies += ['importlib', 'argparse']

distutils.core.setup(
    name='Sarge',
    version='0.3-dev',
    packages=['airship'],
    install_requires=dependencies,
    entry_points={'console_scripts': ['sarge = airship.core:main']},
)
