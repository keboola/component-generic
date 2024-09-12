import unittest
from pathlib import Path

from http_generic.auth import AuthMethodBuilder, AuthBuilderError, BasicHttp
from configuration import WriterConfiguration, ApiConfig, Authentication, ApiRequest, RequestContent


class TestConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        self.resource_dir = Path(__file__).absolute().parent.joinpath('resources').as_posix()

    def test_convert_private(self):
        params = {'#password': 'test'}
        new_args = AuthMethodBuilder._convert_secret_parameters(BasicHttp, **params)
        self.assertDictEqual(new_args, {'_BasicHttp__password': 'test'})

    def test_invalid_method_params_fail(self):
        params = {'#password': 'test'}

        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type='Login'), base_url=''),
            request_parameters=ApiRequest(method='GET', endpoint_path=''),
            request_content=RequestContent(content_type='json')
        )

        with self.assertRaises(ValueError):
            AuthMethodBuilder.build(writer_conf, **params)

    def test_invalid_method_fail(self):
        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type='INVALID'), base_url=''),
            request_parameters=ApiRequest(method='GET', endpoint_path=''),
            request_content=RequestContent(content_type='json')
        )

        with self.assertRaises(AuthBuilderError):
            AuthMethodBuilder.build(writer_conf, **{})

    def test_valid_method_params_pass(self):
        params = {'username': "usr", '#password': 'test'}
        expected = BasicHttp(username='usr', _BasicHttp__password='test')

        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type='BasicHttp'), base_url=''),
            request_parameters=ApiRequest(method='GET', endpoint_path=''),
            request_content=RequestContent(content_type='json')
        )

        auth_method = AuthMethodBuilder.build(writer_conf, **params)
        self.assertEqual(expected, auth_method)
