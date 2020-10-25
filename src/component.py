'''
Template Component main class.

'''

import base64
import csv
import glob
import gzip
import io
import json
import logging
import shutil
import sys

import requests
from csv2json.hone_csv2json import Csv2JsonConverter
from kbc.env_handler import KBCEnvHandler
from nested_lookup import nested_lookup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# configuration variables
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


class Component(KBCEnvHandler):

    def __init__(self, debug=False):
        KBCEnvHandler.__init__(self, MANDATORY_PARS, log_level=logging.DEBUG if debug else logging.INFO)
        # override debug from config
        if self.cfg_params.get(KEY_DEBUG):
            debug = True
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        logging.info('Running version %s', APP_VERSION)
        logging.info('Loading configuration...')

        try:
            self.validate_config(MANDATORY_PARS)
        except ValueError as e:
            logging.exception(e)
            exit(1)

        # intialize instance parameteres
        self.user_functions = Component.UserFunctions(self)
        self.method = self.cfg_params.get(KEY_METHOD, 'POST')

    def run(self):
        '''
        Main execution code
        '''
        params = self.cfg_params  # noqa

        logging.info('Processing input mapping.')

        in_tables = glob.glob(self.tables_in_path + "/*[!.manifest]")

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
            iteration_data = self._get_iter_data(in_table)
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

            headers_cfg = params.get(KEY_HEADERS, {}).copy()
            additional_params_cfg = params.get(KEY_ADDITIONAL_PARS, []).copy()
            # merge iter params
            user_params = {**self.cfg_params.get(KEY_USER_PARS).copy(), **iter_params}
            path = params[KEY_PATH]
            path = self._apply_iteration_params(path, iter_params)
            if has_iterations and log_output:
                logging.info(f'Running iteration nr. {index}')
            if log_output:
                logging.info("Building parameters..")
            # evaluate user_params inside the user params itself
            user_params = self._fill_in_user_parameters(user_params, user_params)
            headers_cfg = self._fill_in_user_parameters(headers_cfg, user_params)
            additional_params_cfg = self._fill_in_user_parameters(additional_params_cfg, user_params)
            # build headers
            headers = {}
            if params.get(KEY_HEADERS):
                for h in headers_cfg:
                    headers[h["key"]] = h["value"]

            # build additional parameters
            additional_params = {}
            if additional_params_cfg:
                for h in additional_params_cfg:
                    # convert boolean
                    val = h["value"]
                    if isinstance(val, str) and val.lower() in ['false', 'true']:
                        val = val.lower() in ['true']
                    additional_params[h["key"]] = val

            additional_params['headers'] = headers

            if log_output and log_output:
                logging.info(f'Sending data in mode: {params[KEY_MODE]}, using {params[KEY_METHOD]} method')

            if params[KEY_MODE] == 'JSON':
                json_cfg = params[KEY_JSON_DATA_CFG]
                json_cfg = self._fill_in_user_parameters(json_cfg, self.cfg_params.get(KEY_USER_PARS))
                if not in_stream:
                    in_stream = open(in_table, mode='rt', encoding='utf-8')

                self.send_json_data(json_cfg, in_stream, path, additional_params, log=not has_iterations)

            elif params[KEY_MODE] == 'EMPTY_REQUEST':
                # send empty request
                self.send_request(path, additional_params, method=self.method)

            elif params[KEY_MODE] in ['BINARY', 'BINARY_GZ']:
                if not in_stream:
                    in_stream = open(in_table, mode='rb')
                else:
                    in_stream = io.BytesIO(bytes(in_stream.getvalue(), 'utf-8'))
                self.send_binary_data(path, params[KEY_MODE], additional_params, in_stream, in_table)

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
            path = path.replace('{{' + p + '}}', iter_params[p])
        return path

    def _create_iteration_data_table(self, iter_data_row):

        # out_file_path = os.path.join(self.tables_in_path, 'iterationdata.csv')
        output_stream = io.StringIO()
        writer = csv.DictWriter(output_stream, fieldnames=iter_data_row.keys(), lineterminator='\n')
        writer.writeheader()
        writer.writerow(iter_data_row)
        output_stream.seek(0)
        return output_stream

    # TODO: separate client and use the Client lib instance
    # TODO: Add support for retry and backoff configuration
    def send_request(self, url, additional_params, method='POST'):
        s = requests.Session()
        r = self._requests_retry_session(session=s).request(method, url, **additional_params)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            logging.error(f'Sending request failed: {r.text}. {e}')
            sys.exit(1)

    def send_json_data(self, params, in_stream, url, additional_request_params, log=True):
        # returns nested JSON schema for input.csv

        reader = csv.reader(in_stream, lineterminator='\n')
        # convert rows
        # skip header
        header = next(reader, None)
        conv = Csv2JsonConverter(header, delimiter=params[KEY_DELIMITER])

        i = 1
        for json_payload in self.convert_csv_2_json_in_chunks(reader, conv, params):
            if log:
                logging.info(f'Sending JSON data chunk {i}')
            json_payload = self._wrap_json_payload(params.get(KEY_REQUEST_DATA_WRAPPER, None), json_payload)

            logging.debug(f'Sending  Payload: {json_payload} ')
            additional_request_params['json'] = json_payload
            self.send_request(url, additional_request_params, method=self.method)
            i += 1
        in_stream.close()

    def convert_csv_2_json_in_chunks(self, reader, converter: Csv2JsonConverter, params):
        col_types = params.get(KEY_COLUMN_TYPES, [])
        delimiter = params[KEY_DELIMITER]
        chunk_size = params.get(KEY_CHUNK_SIZE, None)
        infer_undefined = params.get(KEY_INFER_TYPES, False)
        colname_override = params.get(KEY_NAMES_OVERRIDE, {})
        # fetch first row
        row = next(reader, None)
        if not row:
            logging.warning('The file is empty!')

        while row:  # outer loop, create chunks
            continue_it = True
            i = 0
            json_string = '[' if chunk_size > 1 else ''
            while continue_it:
                i += 1
                result = converter.convert_row(row=row,
                                               coltypes=col_types,
                                               delimit=delimiter,
                                               colname_override=colname_override,
                                               infer_undefined=infer_undefined)

                json_string += json.dumps(result[0])
                row = next(reader, None)

                if not row or (chunk_size and i >= chunk_size):
                    continue_it = False

                if continue_it:
                    json_string += ','

            json_string += ']' if chunk_size > 1 else ''
            yield json.loads(json_string)

    def _wrap_json_payload(self, wrapper_template: str, data: dict):
        if not wrapper_template:
            return data
        res = wrapper_template.replace('{{data}}', json.dumps(data))
        return json.loads(res)

    def send_binary_data(self, url, mode, additional_request_params, in_stream, in_path):
        if mode == 'BINARY_GZ':
            with gzip.open(in_path + '.gz', 'wb') as f_out:
                shutil.copyfileobj(in_stream, f_out)
            in_stream = open(in_path + '.gz', mode='rb')

        additional_request_params['data'] = in_stream
        self.send_request(url, additional_request_params, method=self.method)
        in_stream.close()

    def _requests_retry_session(self, session=None):
        session = session or requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            read=MAX_RETRIES,
            connect=MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=STATUS_FORCELIST,
            method_whitelist=('GET', 'POST', 'PATCH', 'UPDATE', 'PUT')
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

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

    class UserFunctions:
        """
        Custom function to be used in configruation
        """

        def __init__(self, component: KBCEnvHandler):
            # get access to the environment
            self.kbc_env = component

        def validate_function_name(self, function_name):
            supp_functions = self.get_supported_functions()
            if function_name not in self.get_supported_functions():
                raise ValueError(
                    F"Specified user function [{function_name}] is not supported! "
                    F"Supported functions are {supp_functions}")

        @staticmethod
        def get_supported_functions():
            return [method_name for method_name in dir(Component.UserFunctions)
                    if callable(getattr(Component.UserFunctions, method_name)) and not method_name.startswith('__')]

        def execute_function(self, function_name, *pars):
            self.validate_function_name(function_name)
            return getattr(Component.UserFunctions, function_name)(self, *pars)

        def string_to_date(self, date_string, date_format='%Y-%m-%d'):
            start_date, end_date = self.kbc_env.get_date_period_converted(date_string, date_string)
            return start_date.strftime(date_format)

        def concat(self, *args):
            return ''.join(args)

        def base64_encode(self, s):
            return base64.b64encode(s.encode('utf-8')).decode('utf-8')


"""
        Main entrypoint
"""
if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_arg = sys.argv[1]
    else:
        debug_arg = False
    try:
        comp = Component(debug_arg)
        comp.run()
    except Exception as exc:
        logging.exception(exc)
        exit(1)
