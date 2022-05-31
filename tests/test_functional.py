import os
import re
import unittest
from pathlib import Path

import responses
from keboola.component import UserException

from component import Component
from http_generic.client import ClientException
from tests.functional.custom_matchers import binary_payload_matcher, binary_gz_payload_matcher, \
    binary_payload_multi_matcher_to_string


class TestComponent(unittest.TestCase):

    def setUp(self) -> None:
        self.tests_dir = Path(__file__).absolute().parent.joinpath('functional').as_posix()
        self.sample_data_dir = Path(__file__).absolute().parent.joinpath('functional', 'sample_data').as_posix()

    def _get_test_component(self, test_name):
        test_dir = os.path.join(self.tests_dir, test_name)
        os.environ['KBC_DATADIR'] = test_dir
        return Component()

    @responses.activate
    def test_binary_payload_iterations(self):
        test_name = 'binary_iterations'
        comp = self._get_test_component(test_name)

        # expected
        expected_parameters = {"dryrun": "True", "date": "2021-01-01"}
        params_matcher = responses.matchers.query_param_matcher(expected_parameters)

        with open(os.path.join(self.tests_dir, test_name, 'content1.request')) as c1:
            content1 = c1.read()
        with open(os.path.join(self.tests_dir, test_name, 'content2.request')) as c2:
            content2 = c2.read()

        expected_payloads = {
            'http://functional/test/123': content1,
            'http://functional/test/234': content2
        }

        responses.add(
            responses.POST,
            re.compile('http://functional/test/(123|234)'),
            match=[
                binary_payload_multi_matcher_to_string(expected_payloads),
                params_matcher
            ]
        )
        comp.run()

    @responses.activate
    def test_binary_payload_full_table(self):
        test_name = 'binary_simple'
        comp = self._get_test_component(test_name)

        # expected
        expected_data_path = os.path.join(comp.tables_in_path, 'orders.csv')
        expected_parameters = {"dryrun": "True", "date": "2021-01-01"}
        data_matcher = binary_payload_matcher(expected_data_path)
        params_matcher = responses.matchers.query_param_matcher(expected_parameters)

        responses.add(
            responses.POST,
            url="http://functional/test",
            match=[
                data_matcher,
                params_matcher
            ]
        )
        comp.run()

    @responses.activate
    def test_binary_payload_gz(self):
        test_name = 'binary_gz'
        comp = self._get_test_component(test_name)

        # expected
        expected_data_path = os.path.join(comp.tables_in_path, 'orders.csv')
        expected_parameters = {"dryrun": "True", "date": "2021-01-01"}
        data_matcher = binary_gz_payload_matcher(expected_data_path)
        params_matcher = responses.matchers.query_param_matcher(expected_parameters)

        responses.add(
            responses.POST,
            url="http://functional/test",
            match=[
                data_matcher,
                params_matcher
            ]
        )
        comp.run()

    def test_invalid_config_ue(self):
        test_name = 'invalid_config'
        comp = self._get_test_component(test_name)
        try:
            comp.run()
        except UserException as e:
            self.assertIn('Configuration is missing following required fields:', str(e))

    @responses.activate
    def test_log_error_response_content(self):
        test_name = 'simple_retry'
        comp = self._get_test_component(test_name)
        response_text = '{"error": "Request invalid"}'

        responses.add(
            responses.POST,
            url="https://functional/test",
            body=response_text,
            status=400

        )
        try:
            comp.run()
        except ClientException as e:
            self.assertIn(response_text, str(e))


if __name__ == "__main__":
    unittest.main()
