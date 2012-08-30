import sys
import distutils.core

dependencies = ['supervisor', 'blinker', 'path.py', 'PyYAML']
if sys.version_info < (2, 7):
    dependencies += ['importlib', 'argparse']

distutils.core.setup(
    name='Sarge',
    version='0.2-dev',
    packages=['sarge'],
    install_requires=dependencies,
    entry_points={'console_scripts': ['sarge = sarge.core:main']},
)
