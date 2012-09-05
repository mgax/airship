import json
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from path import path
from mock import patch
from importlib import import_module as imp


class HandyTestCase(unittest.TestCase):

    def patch(self, name):
        p = patch(name)
        mock_ob = p.start()
        self.addCleanup(p.stop)
        return mock_ob

    def _pre_setup(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def __call__(self, result=None):
        self._pre_setup()
        super(HandyTestCase, self).__call__(result)


class SargeTestCase(HandyTestCase):

    def sarge(self, config=None):
        if config is None:
            config = {}
        cfg_path = self.tmp / 'etc' / 'sarge.yaml'
        if cfg_path.isfile():
            with open(cfg_path, 'rb') as f:
                config.update(json.load(f))
        config['home'] = self.tmp
        return imp('sarge').Sarge(config)

    def signal(self, name):
        return imp('sarge.signals')._signals[name]

    def _pre_setup(self):
        super(SargeTestCase, self)._pre_setup()
        (self.tmp / 'etc').mkdir()
        self.mock_subprocess = self.patch('sarge.daemons.subprocess')
