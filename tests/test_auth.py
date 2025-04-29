import unittest
from pathlib import Path

from http_generic.auth import AuthMethodBuilder, AuthBuilderError, BasicHttp, OAuth20ClientCredentials
from configuration import WriterConfiguration, ApiConfig, Authentication, ApiRequest, RequestContent


class TestConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self.resource_dir = Path(__file__).absolute().parent.joinpath("resources").as_posix()

    def test_convert_private(self):
        params = {"#password": "test"}
        new_args = AuthMethodBuilder._convert_secret_parameters(BasicHttp, **params)
        self.assertDictEqual(new_args, {"_BasicHttp__password": "test"})

    def test_invalid_method_params_fail(self):
        params = {"#password": "test"}

        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type="Login"), base_url=""),
            request_parameters=ApiRequest(method="GET", endpoint_path=""),
            request_content=RequestContent(content_type="json"),
        )

        with self.assertRaises(ValueError):
            AuthMethodBuilder.build(writer_conf, **params)

    def test_invalid_method_fail(self):
        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type="INVALID"), base_url=""),
            request_parameters=ApiRequest(method="GET", endpoint_path=""),
            request_content=RequestContent(content_type="json"),
        )

        with self.assertRaises(AuthBuilderError):
            AuthMethodBuilder.build(writer_conf, **{})

    def test_valid_method_params_pass(self):
        params = {"username": "usr", "#password": "test"}
        expected = BasicHttp(username="usr", _BasicHttp__password="test")

        writer_conf = WriterConfiguration(
            api=ApiConfig(authentication=Authentication(type="BasicHttp"), base_url=""),
            request_parameters=ApiRequest(method="GET", endpoint_path=""),
            request_content=RequestContent(content_type="json"),
        )

        auth_method = AuthMethodBuilder.build(writer_conf, **params)
        self.assertEqual(expected, auth_method)

    # def test_client_credentials_basic(self):
    #     auth = OAuth20ClientCredentials(
    #         login_endpoint="http://mock-server:80/035-oauth_basic/login",
    #         client_id="clientId",
    #         client_secret="clientSecret",
    #         api_request_headers={"X-ApiToken": {"response": "access_token"}},
    #     )
    #     auth.login()
    #     self.assertEqual(auth.api_request_headers, {"X-ApiToken": "mkoijn098uhbygv"})

    # def test_client_credentials_json(self):
    #     auth = OAuth20ClientCredentials(
    #         method="POST",
    #         auth_type="client_secret_post_json",
    #         login_endpoint="http://mock-server:80/036-oauth_post_json/login",
    #         client_id="clientId",
    #         client_secret="clientSecret",
    #         api_request_headers={"X-ApiToken": {"response": "access_token"}},
    #     )
    #     auth.login()
    #     self.assertEqual(auth.api_request_headers, {"X-ApiToken": "mkoijn098uhbygv"})

    # def test_client_credentials_form(self):
    #     auth = OAuth20ClientCredentials(
    #         method="GET",
    #         auth_type="client_secret_post_form",
    #         login_endpoint="http://mock-server:80/037-oauth_post_form/login",
    #         client_id="id",
    #         client_secret="sec",
    #         api_request_headers={"X-ApiToken": {"response": "access_token"}},
    #     )
    #     auth.login()
    #     self.assertEqual(auth.api_request_headers, {"X-ApiToken": "mkoijn098uhbygv"})
