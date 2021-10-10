'''
Template Component main class.

'''

import csv
import gzip
import io
import json
import logging
import os
import shutil
import tempfile
from urllib.parse import urlparse

from keboola.component import UserException
from keboola.component.base import ComponentBase
from nested_lookup import nested_lookup

# configuration variables
from http_generic.client import GenericHttpClient
from json_converter import JsonConverter
from user_functions import UserFunctions

KEY_USER_PARS = 'user_parameters'

KEY_PATH = 'path'
KEY_MODE = 'mode'
KEY_METHOD = 'method'
# JSON config params
KEY_JSON_DATA_CFG = 'json_data_config'
KEY_DELIMITER = 'delimiter'
KEY_COLUMN_TYPES = 'column_types'
KEY_REQUEST_DATA_WRAPPER = "request_data_wrapper"
KEY_INFER_TYPES = "infer_types_for_unknown"
KEY_NAMES_OVERRIDE = 'column_names_override'

# additional request params
KEY_HEADERS = 'headers'
KEY_ADDITIONAL_PARS = 'additional_requests_pars'
KEY_CHUNK_SIZE = 'chunk_size'
STATUS_FORCELIST = (500, 501, 502, 503)
MAX_RETRIES = 10

KEY_ITERATION_MODE = 'iteration_mode'
KEY_ITERATION_PAR_COLUMNS = 'iteration_par_columns'
# #### Keep for debug
KEY_DEBUG = 'debug'

MANDATORY_PARS = [KEY_PATH]
MANDATORY_IMAGE_PARS = []

SUPPORTED_MODES = ['JSON', 'BINARY', 'BINARY-GZ']

APP_VERSION = '0.0.1'


class Component(ComponentBase):

    def __init__(self):
        super().__init__()

        # intialize instance parameteres
        self.user_functions = UserFunctions()
        self.validate_configuration_parameters(MANDATORY_PARS)

        self.method = self.configuration.parameters.get(KEY_METHOD, 'POST')
        path = self.configuration.parameters[KEY_PATH]
        base_url = urlparse(path).netloc
        self.endpoint = urlparse(path).path
        self._client = GenericHttpClient(base_url=base_url)

        self.content_type = self.configuration.parameters[KEY_MODE]

    def run(self):
        '''
        Main execution code
        '''
        params = self.configuration.parameters  # noqa

        logging.info('Processing input mapping.')

        in_tables = self.get_input_tables_definitions()

        if len(in_tables) == 0:
            logging.exception('There is no table specified on the input mapping! You must provide one input table!')
            exit(1)
        elif len(in_tables) > 1:
            logging.warning(
                'There is more than one table specified on the input mapping! You must provide one input table!')

        in_table = in_tables[0]

        # iteration mode
        iteration_mode = params.get(KEY_ITERATION_MODE)
        iteration_data = [{}]
        has_iterations = False

        # TODO: add support for "chunked" iteration mode, sending requests in bulk grouped by iteration parameters
        if iteration_mode:
            has_iterations = True
            iteration_data = self._get_iter_data(in_table.full_path)
            logging.warning('Iteration parameters mode found, running multiple iterations.')

        # runing iterations
        for index, iter_data_row in enumerate(iteration_data):
            iter_params = {}
            log_output = (index % 50) == 0
            in_stream = None
            if has_iterations:
                iter_params = self._cut_out_iteration_params(iter_data_row, iteration_mode)
                # change source table with iteration data row
                in_stream = self._create_iteration_data_table(iter_data_row)

            # merge iter params
            user_params = {**params.get(KEY_USER_PARS).copy(), **iter_params}
            # evaluate user_params inside the user params itself
            user_params = self._fill_in_user_parameters(user_params, user_params)

            # build headers
            headers_cfg = params.get(KEY_HEADERS, {}).copy()
            headers_cfg = self._fill_in_user_parameters(headers_cfg, user_params)
            headers = self._build_http_headers(headers_cfg)

            # build additional parameters
            additional_params_cfg = params.get(KEY_ADDITIONAL_PARS, []).copy()
            additional_params_cfg = self._fill_in_user_parameters(additional_params_cfg, user_params)
            additional_params = self._build_request_parameters(additional_params_cfg)

            additional_params['headers'] = headers

            path = params[KEY_PATH]
            path = self._apply_iteration_params(path, iter_params)

            if has_iterations and log_output:
                logging.info(f'Running iteration nr. {index}')
            if log_output:
                logging.info("Building parameters..")

            if log_output and log_output:
                logging.info(f'Sending data in mode: {params[KEY_MODE]}, using {params[KEY_METHOD]} method')

            if self.content_type in ['JSON', 'JSON_URL_ENCODED']:
                if not in_stream:
                    # if no iterations
                    in_stream = open(in_table.full_path, mode='rt', encoding='utf-8')
                self.send_json_data(in_stream, path, additional_params, log=not has_iterations)

            elif self.content_type == 'EMPTY_REQUEST':
                # send empty request
                self._client.send_request(method=self.method, url=path, **additional_params)

            elif self.content_type in ['BINARY', 'BINARY_GZ']:
                if not in_stream:
                    in_stream = open(in_table.full_path, mode='rb')
                else:
                    # in case of iteration mode
                    in_stream = io.BytesIO(bytes(in_stream.getvalue(), 'utf-8'))
                self.send_binary_data(path, params[KEY_MODE], additional_params, in_stream, in_table.full_path)

        logging.info("Writer finished")

    def _get_iter_data(self, iteration_pars_path):
        with open(iteration_pars_path, mode='rt', encoding='utf-8') as in_file:
            reader = csv.DictReader(in_file, lineterminator='\n')
            for r in reader:
                yield r

    def _cut_out_iteration_params(self, iter_data_row, iteration_mode):
        '''
        Cuts out iteration columns from data row and returns current iteration parameters values
        :param iter_data_row:
        :param iteration_mode:
        :return:
        '''
        params = {}
        for c in iteration_mode.get(KEY_ITERATION_PAR_COLUMNS):
            params[c] = iter_data_row.pop(c)
        return params

    def _apply_iteration_params(self, path, iter_params):
        for p in iter_params:
            # backward compatibility with {{}} syntax
            path = path.replace('{{' + p + '}}', iter_params[p])
            path = path.replace('[[' + p + ']]', iter_params[p])
        return path

    def _create_iteration_data_table(self, iter_data_row):
        # out_file_path = os.path.join(self.tables_in_path, 'iterationdata.csv')
        output_stream = io.StringIO()
        writer = csv.DictWriter(output_stream, fieldnames=iter_data_row.keys(), lineterminator='\n')
        writer.writeheader()
        writer.writerow(iter_data_row)
        output_stream.seek(0)
        return output_stream

    def _build_http_headers(self, headers_cfg):
        headers = {}
        if self.configuration.parameters.get(KEY_HEADERS):
            for h in headers_cfg:
                headers[h["key"]] = h["value"]
        return headers

    def _build_request_parameters(self, request_configuration):
        request_parameters = {}
        for h in request_configuration:
            # convert boolean
            val = h["value"]
            if isinstance(val, str) and val.lower() in ['false', 'true']:
                val = val.lower() in ['true']
            request_parameters[h["key"]] = val
        return request_parameters

    def send_json_data(self, in_stream, url, additional_request_params, log=True):
        # returns nested JSON schema for input.csv
        params = self.configuration.parameters[KEY_JSON_DATA_CFG]

        if self.content_type == 'JSON_URL_ENCODED':
            logging.warning('Running in JSON_URL_ENCODED mode, overriding chunk size to 1')
            params[KEY_CHUNK_SIZE] = 1
            params[KEY_REQUEST_DATA_WRAPPER] = None

        params = self._fill_in_user_parameters(params, self.configuration.parameters.get(KEY_USER_PARS))

        converter = JsonConverter(nesting_delimiter=params[KEY_DELIMITER],
                                  chunk_size=params.get(KEY_CHUNK_SIZE),
                                  infer_data_types=params.get(KEY_INFER_TYPES, False),
                                  column_data_types=params.get(KEY_COLUMN_TYPES),
                                  column_name_override=params.get(KEY_NAMES_OVERRIDE, {}),
                                  data_wrapper=params.get(KEY_REQUEST_DATA_WRAPPER))

        reader = csv.reader(in_stream, lineterminator='\n')

        # convert rows
        i = 1
        for json_payload in converter.convert_stream(reader):
            if log:
                logging.info(f'Sending JSON data chunk {i}')
            logging.debug(f'Sending  Payload: {json_payload} ')

            if self.content_type == 'JSON':
                additional_request_params['json'] = json_payload
            elif self.content_type == 'JSON_URL_ENCODED':
                additional_request_params['data'] = json_payload
            else:
                raise ValueError(f"Invalid JSON content type: {self.content_type}")

            self._client.send_request(method=self.method, url=url, **additional_request_params)
            i += 1
        in_stream.close()

    def send_binary_data(self, url, mode, additional_request_params, in_stream, in_path):
        if mode == 'BINARY_GZ':
            file = tempfile.mktemp()
            with gzip.open(file, 'wb') as f_out:
                shutil.copyfileobj(in_stream, f_out)

            in_stream = open(file, mode='rb')

            additional_request_params['data'] = in_stream
            self._client.send_request(method=self.method, url=url, **additional_request_params)
            in_stream.close()
            os.remove(file)

    def _fill_in_user_parameters(self, conf_objects, user_param):
        # convert to string minified
        steps_string = json.dumps(conf_objects, separators=(',', ':'))
        # dirty and ugly replace
        for key in user_param:
            if isinstance(user_param[key], dict):
                # in case the parameter is function, validate, execute and replace value with result
                user_param[key] = self._perform_custom_function(key, user_param[key], user_param)

            lookup_str = '{"attr":"' + key + '"}'
            steps_string = steps_string.replace(lookup_str, '"' + str(user_param[key]) + '"')
        new_steps = json.loads(steps_string)
        non_matched = nested_lookup('attr', new_steps)

        if non_matched:
            raise ValueError(
                'Some user attributes [{}] specified in configuration '
                'are not present in "user_parameters" field.'.format(non_matched))
        return new_steps

    def _perform_custom_function(self, key, function_cfg, user_params):
        if function_cfg.get('attr'):
            return user_params[function_cfg['attr']]
        if not function_cfg.get('function'):
            raise ValueError(
                F'The user parameter {key} value is object and is not a valid function object: {function_cfg}')
        new_args = []
        for arg in function_cfg.get('args'):
            if isinstance(arg, dict):
                arg = self._perform_custom_function(key, arg, user_params)
            new_args.append(arg)
        function_cfg['args'] = new_args

        return self.user_functions.execute_function(function_cfg['function'], *function_cfg.get('args'))


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action paramter
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
