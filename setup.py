import sys
import distutils.core

dependencies = ['supervisor', 'flup', 'blinker', 'path.py']
if sys.version_info < (2, 7):
    dependencies += ['importlib', 'argparse']

distutils.core.setup(
    name='Sarge',
    version='0.1',
    py_modules=['sarge'],
    install_requires=dependencies,
)
