"""
Created on 12. 11. 2018

@author: esner
"""

import json
import os
import shutil
import tempfile
import unittest

import mock
from freezegun import freeze_time
from keboola.component import UserException

from component import Component
from user_functions import UserFunctions


def _build_config(base_url, authentication=None) -> dict:
    """
    Builds a minimal valid v2 configuration, with `api.base_url` set to the supplied value.
    """
    api = {"base_url": base_url}
    if authentication:
        api["authentication"] = authentication
    return {
        "parameters": {
            "api": api,
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


class TestComponent(unittest.TestCase):
    # set global time to 2010-10-10 - affects functions like datetime.now()
    @freeze_time("2010-10-10")
    # set KBC_DATADIR env to non-existing dir
    @mock.patch.dict(os.environ, {"KBC_DATADIR": "./non-existing-dir"})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()

    def _init_component(self, base_url, authentication=None) -> Component:
        """
        Runs Component.init_component() against a throwaway datadir built from the given api config.
        """
        datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, datadir, ignore_errors=True)
        with open(os.path.join(datadir, "config.json"), "w") as cfg_file:
            json.dump(_build_config(base_url, authentication), cfg_file)

        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir}):
            comp = Component()
            comp.init_component()
            return comp

    def test_object_base_url_raises_user_exception(self):
        """
        A non-string `api.base_url` (e.g. an unresolved {"attr": ...} reference) used to crash
        with an opaque AttributeError ('dict' object has no attribute 'endswith') and exit code 2.
        It must now surface as a UserException (exit code 1) naming the offending parameter.
        """
        with self.assertRaises(UserException) as ctx:
            self._init_component({"attr": "some_user_parameter"})

        self.assertIn("api.base_url", str(ctx.exception))
        self.assertIn("dict", str(ctx.exception))

    def test_object_base_url_raises_user_exception_with_login_auth(self):
        """
        With a Login/OAuth auth method the base_url is joined with the login endpoint while the auth
        method is built, which happens before the client is constructed. That path must also report a
        UserException rather than an opaque AttributeError from urljoin.
        """
        authentication = {
            "type": "Login",
            "parameters": {
                "loginRequest": {"endpoint": "/login", "method": "POST"},
                "apiRequest": {"headers": {"X-ApiToken": {"response": "token"}}},
            },
        }
        with self.assertRaises(UserException) as ctx:
            self._init_component({"attr": "some_user_parameter"}, authentication=authentication)

        self.assertIn("api.base_url", str(ctx.exception))

    def test_string_base_url_still_builds_client(self):
        """
        Happy path guard: a plain string base_url must keep initialising the client exactly as before.
        """
        comp = self._init_component("https://example.com")

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
