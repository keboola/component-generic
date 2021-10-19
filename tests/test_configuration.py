import json
import os
import unittest
from pathlib import Path

import configuration
from configuration import ApiRequest, ApiConfig, JsonMapping, WriterConfiguration, RequestContent, RequestOptions, \
    ColumnDataTypes


class TestConfiguration(unittest.TestCase):

    def setUp(self) -> None:
        self.resource_dir = Path(__file__).absolute().parent.joinpath('resources').as_posix()

    def test_validation_passes(self):
        with open(os.path.join(self.resource_dir, 'configv2.json')) as inp:
            config = json.load(inp)
            configuration.validate_configuration_v2(config)

    def test_build_configuration_full(self):
        api = ApiConfig(base_url="http://test.com/api/",
                        authentication=configuration.Authentication(type='SomeType', parameters={"test": "val"}),
                        default_query_parameters={
                            "test": "test"
                        },
                        default_headers=
                        {"Authorization": {
                            "attr": "token_encoded"
                        }
                        },
                        retry_config=configuration.RetryConfig(max_retries=10))
        user_parameters = {
            "debug": True,
            "#token": "Bearer 123456",
            "token_encoded": {
                "function": "concat",
                "args": [
                    "Basic ", {
                        "function": "base64_encode",
                        "args": [{
                            "attr": "#token"
                        }
                        ]
                    }
                ]
            }
        }

        req_options = RequestOptions(
            api_request=ApiRequest(method='POST',
                                   endpoint_path="users/[[id]]",
                                   headers={"endpoint_header": "eh"},
                                   query_parameters={
                                       "date": "[[date]]"
                                   },
                                   continue_on_failure=False),
            content=RequestContent(content_type="JSON",
                                   iterate_by_columns=["id", "date"],
                                   json_mapping=JsonMapping(chunk_size=1,
                                                            nesting_delimiter="__",
                                                            request_data_wrapper="{ \"data\": [[data]]}",
                                                            column_names_override={
                                                                "column_a": "COLUMN|A"
                                                            },
                                                            column_data_types=ColumnDataTypes(
                                                                autodetect=True,
                                                                datatype_override=[
                                                                    {
                                                                        "column_a": "number"
                                                                    }
                                                                ]))))

        expected_cfg = WriterConfiguration(api=api, request_options=req_options, user_parameters=user_parameters)
        with open(os.path.join(self.resource_dir, 'configv2.json')) as inp:
            config = json.load(inp)
            cfg_object = configuration.build_configuration(config)
            self.assertEqual(expected_cfg, cfg_object)

    def test_build_configuration_minimal(self):
        api = ApiConfig(base_url="http://test.com/api/")
        user_parameters = {
            "debug": True,
            "#token": "Bearer 123456",
            "token_encoded": {
                "function": "concat",
                "args": [
                    "Basic ", {
                        "function": "base64_encode",
                        "args": [{
                            "attr": "#token"
                        }
                        ]
                    }
                ]
            }
        }
        req_options = RequestOptions(
            api_request=ApiRequest(method='POST',
                                   endpoint_path="users/[[id]]",
                                   continue_on_failure=False),
            content=RequestContent(content_type="JSON",
                                   iterate_by_columns=["id", "date"],
                                   json_mapping=JsonMapping(chunk_size=1,
                                                            nesting_delimiter="__",
                                                            column_data_types=ColumnDataTypes(
                                                                autodetect=True))))

        expected_cfg = WriterConfiguration(api=api, request_options=req_options, user_parameters=user_parameters)

        with open(os.path.join(self.resource_dir, 'configv2_minimal.json')) as inp:
            config = json.load(inp)
            cfg_object = configuration.build_configuration(config)
            self.assertEqual(expected_cfg, cfg_object)
