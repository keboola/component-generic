"""
Created on 12. 11. 2018

@author: esner
"""

import json
import os
import tempfile
import unittest

import mock
from freezegun import freeze_time
from keboola.component import UserException

from component import Component
from user_functions import UserFunctions


def _build_datadir(base_url) -> str:
    """
    Creates a minimal valid v2 datadir, with `api.base_url` set to the supplied value.
    """
    datadir = tempfile.mkdtemp()
    config = {
        "parameters": {
            "api": {"base_url": base_url},
            "user_parameters": {},
            "request_parameters": {"method": "POST", "endpoint_path": "/orders"},
            "request_content": {
                "content_type": "JSON",
                "json_mapping": {
                    "nesting_delimiter": "__",
                    "chunk_size": 2,
                    "column_data_types": {"autodetect": True},
                    "request_data_wrapper": "",
                    "column_names_override": {},
                },
            },
        }
    }
    with open(os.path.join(datadir, "config.json"), "w") as cfg_file:
        json.dump(config, cfg_file)
    return datadir


class TestComponent(unittest.TestCase):
    # set global time to 2010-10-10 - affects functions like datetime.now()
    @freeze_time("2010-10-10")
    # set KBC_DATADIR env to non-existing dir
    @mock.patch.dict(os.environ, {"KBC_DATADIR": "./non-existing-dir"})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()

    def test_object_base_url_raises_user_exception(self):
        """
        A non-string `api.base_url` (e.g. an unresolved {"attr": ...} reference) used to crash
        with an opaque AttributeError ('dict' object has no attribute 'endswith') and exit code 2.
        It must now surface as a UserException (exit code 1) naming the offending parameter.
        """
        datadir = _build_datadir({"attr": "some_user_parameter"})
        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir}):
            comp = Component()
            with self.assertRaises(UserException) as ctx:
                comp.init_component()

        self.assertIn("api.base_url", str(ctx.exception))

    def test_string_base_url_still_builds_client(self):
        """
        Happy path guard: a plain string base_url must keep initialising the client exactly as before.
        """
        datadir = _build_datadir("https://example.com")
        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir}):
            comp = Component()
            comp.init_component()

        self.assertEqual("https://example.com/", comp._client.base_url)


class TestUserFunctions(unittest.TestCase):
    def setUp(self) -> None:
        self.uf = UserFunctions()

    def test_md5_hash(self):
        expected = "99aa06adaa9fdd8f506569e43c29ed25"
        hashed = self.uf.execute_function("md5_encode", "keboola_is_awesome")
        self.assertEqual(expected, hashed)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
