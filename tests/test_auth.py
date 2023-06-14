import unittest
from pathlib import Path

from http_generic.auth import AuthMethodBuilder, AuthBuilderError, BasicHttp


class TestConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        self.resource_dir = Path(__file__).absolute().parent.joinpath('resources').as_posix()

    def test_convert_private(self):
        params = {'#password': 'test'}
        new_args = AuthMethodBuilder._convert_secret_parameters(BasicHttp, **params)
        self.assertDictEqual(new_args, {'_BasicHttp__password': 'test'})

    def test_invalid_method_params_fail(self):
        params = {'#password': 'test'}
        with self.assertRaises(AuthBuilderError):
            AuthMethodBuilder.build('BasicHttp', **params)

    def test_invalid_method_fail(self):
        with self.assertRaises(AuthBuilderError):
            AuthMethodBuilder.build('INVALID', **{})

    def test_valid_method_params_pass(self):
        params = {'username': "usr", '#password': 'test'}
        expected = BasicHttp(None, username='usr', _BasicHttp__password='test')
        auth_method = AuthMethodBuilder.build('BasicHttp', **params)
        self.assertEqual(expected, auth_method)
