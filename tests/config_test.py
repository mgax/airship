import json
from path import path
from common import configure_deployment, imp
from common import SargeTestCase


class DeploymentTest(SargeTestCase):

    def test_enumerate_instances(self):
        instance = self.sarge().new_instance()
        self.assertEqual([d.name for d in self.sarge().deployments],
                         [instance.id_])
