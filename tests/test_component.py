'''
Created on 12. 11. 2018

@author: esner
'''
import os
import unittest

import mock
from freezegun import freeze_time

from component import Component
from user_functions import UserFunctions


class TestComponent(unittest.TestCase):

    # set global time to 2010-10-10 - affects functions like datetime.now()
    @freeze_time("2010-10-10")
    # set KBC_DATADIR env to non-existing dir
    @mock.patch.dict(os.environ, {'KBC_DATADIR': './non-existing-dir'})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()


class TestUserFunctions(unittest.TestCase):

    def setUp(self) -> None:
        self.uf = UserFunctions()

    def test_md5_hash(self):
        expected = '99aa06adaa9fdd8f506569e43c29ed25'
        hashed = self.uf.execute_function('md5_encode', 'keboola_is_awesome')
        self.assertEqual(expected, hashed)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
