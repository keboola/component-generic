"""
Template Component main class.

"""

import csv
import gzip
import io
import logging
import os
import shutil
import sys
import tempfile

from keboola.component import UserException
from keboola.component.base import ComponentBase

# parameters variables
from configuration import WriterConfiguration, build_configuration, ValidationError, ConfigHelpers
from http_generic.auth import AuthMethodBuilder, AuthBuilderError
from http_generic.client import GenericHttpClient
from json_converter import JsonConverter
from user_functions import UserFunctions


KEY_USER_PARS = "user_parameters"

KEY_PATH = "path"
KEY_MODE = "mode"
KEY_METHOD = "method"
# JSON config params
KEY_JSON_DATA_CFG = "json_data_config"
KEY_DELIMITER = "delimiter"
KEY_COLUMN_TYPES = "column_types"
KEY_REQUEST_DATA_WRAPPER = "request_data_wrapper"
KEY_INFER_TYPES = "infer_types_for_unknown"
KEY_NAMES_OVERRIDE = "column_names_override"

# additional request params
KEY_HEADERS = "headers"
KEY_ADDITIONAL_PARS = "additional_requests_pars"
KEY_CHUNK_SIZE = "chunk_size"
STATUS_FORCELIST = (500, 501, 502, 503)
MAX_RETRIES = 10

KEY_ITERATION_MODE = "iteration_mode"
KEY_ITERATION_PAR_COLUMNS = "iteration_par_columns"
# #### Keep for debug
KEY_DEBUG = "debug"

MANDATORY_PARS = [KEY_PATH]
MANDATORY_IMAGE_PARS = []

SUPPORTED_MODES = ["JSON", "BINARY", "BINARY-GZ"]

APP_VERSION = "0.0.1"


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

        # initialize instance parameters
        self.user_functions = UserFunctions()

        self._configuration: WriterConfiguration = None
        self._client: GenericHttpClient = None

    def init_component(self):
        try:
            self._configuration = build_configuration(self.configuration.parameters)
        except ValidationError as e:
            raise UserException(e) from e

        # build authentication method
        auth_method = None
        authentication = self._configuration.api.authentication

        try:
            if authentication:
                # evaluate user_params inside the user params itself
                user_params = self._configuration.user_parameters
                user_params = ConfigHelpers().fill_in_user_parameters(user_params, user_params)
                # apply user parameters
                auth_method_params = ConfigHelpers().fill_in_user_parameters(authentication.parameters, user_params)
                auth_method = AuthMethodBuilder.build(self.configuration, **auth_method_params)
        except AuthBuilderError as e:
            raise UserException(e) from e

        # init client
        self._client = GenericHttpClient(
            base_url=self._configuration.api.base_url,
            max_retries=self._configuration.api.retry_config.max_retries,
            backoff_factor=self._configuration.api.retry_config.backoff_factor,
            status_forcelist=self._configuration.api.retry_config.codes,
            auth_method=auth_method,
        )
        # to prevent field larger than field limit (131072) Errors
        # https://stackoverflow.com/questions/15063936/csv-error-field-larger-than-field-limit-131072
        csv.field_size_limit(sys.maxsize)

    def run(self):
        """
        Main execution code
        """
        self.init_component()
        # login if auth method specified
        self._client.login()

        logging.info("Processing input mapping.")

        in_tables = self.get_input_tables_definitions()

        if len(in_tables) == 0:
            logging.exception("There is no table specified on the input mapping! You must provide one input table!")
            exit(1)
        elif len(in_tables) > 1:
            logging.warning(
                "There is more than one table specified on the input mapping! You must provide one input table!"
            )

        in_table = in_tables[0]

        api_cfg = self._configuration.api
        content_cfg = self._configuration.request_content
        request_cfg = self._configuration.request_parameters
        # iteration mode
        iteration_mode = content_cfg.iterate_by_columns
        iteration_data = [{}]
        has_iterations = False

        # TODO: add support for "chunked" iteration mode, sending requests in bulk grouped by iteration parameters
        if iteration_mode:
            has_iterations = True
            iteration_data = self._get_iter_data(in_table.full_path)
            logging.warning("Iteration parameters mode found, running multiple iterations.")
        logging.info(f"Sending data in content type: {content_cfg.content_type}, using {request_cfg.method} method")
        # running iterations
        for index, iter_data_row in enumerate(iteration_data):
            iter_params = {}
            log_output = (index % 50) == 0
            in_stream = None
            if has_iterations:
                iter_params = self._cut_out_iteration_params(iter_data_row)
                # change source table with iteration data row
                in_stream = self._create_iteration_data_table(iter_data_row)

            # merge iter params
            # fix KBC bug
            user_params = self._configuration.user_parameters
            user_params = {**user_params.copy(), **iter_params}
            # evaluate user_params inside the user params itself
            user_params = ConfigHelpers().fill_in_user_parameters(user_params, user_params)

            # build headers
            headers = {**api_cfg.default_headers.copy(), **request_cfg.headers.copy()}
            new_headers = ConfigHelpers().fill_in_user_parameters(headers, user_params)

            # build additional parameters
            query_parameters = {**api_cfg.default_query_parameters.copy(), **request_cfg.query_parameters.copy()}
            query_parameters = ConfigHelpers().fill_in_user_parameters(query_parameters, user_params)
            timeout = api_cfg.timeout

            # SSL verification parameters
            # if user provided CA certificate or client certificate & key, those will be written to a temp file and used
            if not api_cfg.ca_cert:
                ca_cert_file = ""
            else:
                with tempfile.NamedTemporaryFile("w", delete=False) as cafp:
                    ca_cert_file = cafp.name
                    cafp.write(api_cfg.ca_cert)

            if not api_cfg.client_cert_key:
                client_cert_key_file = ""
            else:
                with tempfile.NamedTemporaryFile("w", delete=False) as ccfp:
                    client_cert_key_file = ccfp.name
                    ccfp.write(api_cfg.client_cert_key)

            verify = ca_cert_file if ca_cert_file else api_cfg.ssl_verification

            request_parameters = {
                "params": query_parameters,
                "headers": new_headers,
                "timeout": timeout,
                "verify": verify,
                "cert": client_cert_key_file,
            }

            endpoint_path = request_cfg.endpoint_path
            endpoint_path = self._apply_iteration_params(endpoint_path, iter_params)
            self._client.base_url = self._apply_iteration_params(self._client.base_url, iter_params)

            if has_iterations and log_output:
                logging.info(f"Running iteration nr. {index}")
            if log_output:
                logging.info("Building parameters..")

            if content_cfg.content_type in ["JSON", "JSON_URL_ENCODED"]:
                if not in_stream:
                    # if no iterations
                    in_stream = open(in_table.full_path, mode="rt", encoding="utf-8")
                self.send_json_data(in_stream, endpoint_path, request_parameters, log=not has_iterations)
                in_stream.close()

            elif content_cfg.content_type == "EMPTY_REQUEST":
                # send empty request
                self._client.send_request(method=request_cfg.method, endpoint_path=endpoint_path, **request_parameters)

            elif content_cfg.content_type in ["BINARY", "BINARY_GZ"]:
                if not in_stream:
                    in_stream = open(in_table.full_path, mode="rb")
                else:
                    # in case of iteration mode
                    in_stream = io.BytesIO(bytes(in_stream.getvalue(), "utf-8"))
                self.send_binary_data(endpoint_path, request_parameters, in_stream)
                in_stream.close()

        logging.info("Writer finished")

    def _get_iter_data(self, iteration_pars_path):
        with open(iteration_pars_path, mode="rt", encoding="utf-8") as in_file:
            reader = csv.DictReader(in_file, lineterminator="\n")
            for r in reader:
                yield r

    def _cut_out_iteration_params(self, iter_data_row):
        """
        Cuts out iteration columns from data row and returns current iteration parameters values
        :param iter_data_row:
        :return:
        """
        params = {}
        for c in self._configuration.request_content.iterate_by_columns:
            try:
                params[c] = iter_data_row.pop(c)
            except KeyError:
                raise UserException(
                    f'The key: "{c}" specified in the iterate_by_columns parameter '
                    f"does not exist in the data, please check for typos / case."
                )
        return params

    def _apply_iteration_params(self, path, iter_params):
        for p in iter_params:
            # backward compatibility with {{}} syntax
            path = path.replace("{{" + p + "}}", iter_params[p])
            path = path.replace("[[" + p + "]]", iter_params[p])
        return path

    def _create_iteration_data_table(self, iter_data_row):
        # out_file_path = os.path.join(self.tables_in_path, 'iterationdata.csv')
        output_stream = io.StringIO()
        writer = csv.DictWriter(output_stream, fieldnames=iter_data_row.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow(iter_data_row)
        output_stream.seek(0)
        return output_stream

    def _build_request_parameters(self, request_configuration):
        request_parameters = {}
        for h in request_configuration:
            # convert boolean
            val = h["value"]
            if isinstance(val, str) and val.lower() in ["false", "true"]:
                val = val.lower() in ["true"]
            request_parameters[h["key"]] = val
        return request_parameters

    def send_json_data(self, in_stream, url, additional_request_params, log=True):
        # returns nested JSON schema for input.csv
        request_parameters = self._configuration.request_parameters
        request_content = self._configuration.request_content
        json_params = request_content.json_mapping

        if request_content.content_type == "JSON_URL_ENCODED":
            logging.warning("Running in JSON_URL_ENCODED mode, overriding chunk size to 1")
            json_params.chunk_size = 1
            json_params.request_data_wrapper = None

        converter = JsonConverter(
            nesting_delimiter=json_params.nesting_delimiter,
            chunk_size=json_params.chunk_size,
            infer_data_types=json_params.column_data_types.autodetect,
            column_data_types=json_params.column_data_types.datatype_override,
            column_name_override=json_params.column_names_override,
            data_wrapper=json_params.request_data_wrapper,
        )

        reader = csv.reader(in_stream, lineterminator="\n")

        # convert rows
        i = 1
        for json_payload in converter.convert_stream(reader):
            if log:
                logging.info(f"Sending JSON data chunk {i}")
            logging.debug(f"Sending  Payload: {json_payload} ")

            if request_content.content_type == "JSON":
                additional_request_params["json"] = json_payload
            elif request_content.content_type == "JSON_URL_ENCODED":
                additional_request_params["data"] = json_payload
            else:
                raise ValueError(f"Invalid JSON content type: {request_content.content_type}")

            self._client.send_request(method=request_parameters.method, endpoint_path=url, **additional_request_params)
            i += 1
        in_stream.close()

    def send_binary_data(self, url, additional_request_params, in_stream):
        request_parameters = self._configuration.request_parameters
        request_content = self._configuration.request_content
        file = tempfile.mktemp()
        if request_content.content_type == "BINARY_GZ":
            with gzip.open(file, "wb") as f_out:
                shutil.copyfileobj(in_stream, f_out)

            in_stream = open(file, mode="rb")

        additional_request_params["data"] = in_stream
        self._client.send_request(method=request_parameters.method, endpoint_path=url, **additional_request_params)
        in_stream.close()
        if os.path.exists(file):
            os.remove(file)

    def _perform_custom_function(self, key, function_cfg, user_params):
        if function_cfg.get("attr"):
            return user_params[function_cfg["attr"]]
        if not function_cfg.get("function"):
            raise ValueError(
                f"The user parameter {key} value is object and is not a valid function object: {function_cfg}"
            )
        new_args = []
        for arg in function_cfg.get("args"):
            if isinstance(arg, dict):
                arg = self._perform_custom_function(key, arg, user_params)
            new_args.append(arg)
        function_cfg["args"] = new_args

        return self.user_functions.execute_function(function_cfg["function"], *function_cfg.get("args"))


"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the parameters.action paramter
        comp.execute_action()
    except UserException as exc:
        detail = ""
        if len(exc.args) > 1:
            detail = exc.args[1]

        logging.exception(exc, extra={"full_message": detail})
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
