import unittest
import tempfile
from path import path


def setUpModule(self):
    import sarge; self.sarge = sarge


class ForceSymlinkTest(unittest.TestCase):

    def setUp(self):
        self.tmp = path(tempfile.mkdtemp())
        self.addCleanup(self.tmp.rmtree)

    def test_simple_link(self):
        target = self.tmp/'target'
        target.write_text('bla')
        link = self.tmp/'link'
        sarge.force_symlink(target, link)
        self.assertTrue(link.islink())
        self.assertEqual(link.readlink(), target)

    def test_overwrite_existing_link(self):
        target = self.tmp/'target'
        target.write_text('bla')
        target2 = self.tmp/'target2'
        target2.write_text('foo')
        link = self.tmp/'link'
        target2.symlink(link)
        sarge.force_symlink(target, link)
        self.assertTrue(link.islink())
        self.assertEqual(link.readlink(), target)

    def test_overwrite_existing_broken_link(self):
        target = self.tmp/'target'
        target.write_text('bla')
        target2 = self.tmp/'target2'
        link = self.tmp/'link'
        target2.symlink(link)
        sarge.force_symlink(target, link)
        self.assertTrue(link.islink())
        self.assertEqual(link.readlink(), target)
