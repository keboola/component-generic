import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Literal
from urllib.parse import urlparse, urljoin

from keboola.component.dao import build_dataclass_from_dict
import json
import time
from nested_lookup import nested_lookup
from user_functions import UserFunctions


@dataclass
class SubscriptableDataclass:
    """
    Helper class to make dataclasses subscriptable
    """

    def __getitem__(self, index):
        return getattr(self, index)

    def __setitem__(self, key, value):
        return setattr(self, key, value)


# CONFIGURATION OBJECT
class ContentType(str, Enum):
    none = "none"
    json = "json"
    form = "form"

# #### SUPPORTING DATACLASSES


@dataclass
class RetryConfig(SubscriptableDataclass):
    max_retries: int = 1
    backoff_factor: float = 0.3
    codes: Tuple[int, ...] = (500, 502, 504)


@dataclass
class Authentication(SubscriptableDataclass):
    type: str
    parameters: dict = field(default_factory=dict)


@dataclass
class ApiConfig(SubscriptableDataclass):
    base_url: str
    default_query_parameters: dict = field(default_factory=dict)
    default_headers: dict = field(default_factory=dict)
    authentication: Authentication = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    ssl_verification: bool = True
    timeout: float = None


@dataclass
class ApiRequest(SubscriptableDataclass):
    method: str
    endpoint_path: str
    headers: dict = field(default_factory=dict)
    query_parameters: dict = field(default_factory=dict)
    continue_on_failure: bool = False


class DataType(Enum):
    bool = 'bool'
    string = 'string'
    number = 'number'
    object = 'object'


@dataclass
class ColumnDataTypes(SubscriptableDataclass):
    autodetect: bool = False
    datatype_override: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class JsonMapping(SubscriptableDataclass):
    nesting_delimiter: str
    chunk_size: int
    column_data_types: ColumnDataTypes
    request_data_wrapper: str = ''
    column_names_override: dict = field(default_factory=dict)


@dataclass
class RequestContent(SubscriptableDataclass):
    content_type: str
    json_mapping: JsonMapping = None
    iterate_by_columns: List[str] = None
    query_parameters: dict = field(default_factory=dict)
    body: Optional[dict] = None


# CONFIGURATION OBJECT

@dataclass
class WriterConfiguration(SubscriptableDataclass):
    api: ApiConfig
    request_parameters: ApiRequest
    request_content: RequestContent
    user_parameters: dict = field(default_factory=dict)


class ConfigurationKeysV2(Enum):
    api = 'api'
    user_parameters = 'user_parameters'
    request_options = 'request_options'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class ConfigurationKeysV1(Enum):
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
    KEY_ITERATION_MODE = 'iteration_mode'
    KEY_ITERATION_PAR_COLUMNS = 'iteration_par_columns'

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


def get_dataclass_required_params(data_class):
    return [f.name for f in dataclasses.fields(data_class)
            if f.default == dataclasses.MISSING
            and f.default_factory == dataclasses.MISSING]


def _is_v2_config(configuration: dict):
    return 'path' in list(configuration.keys())


def convert_to_v2(parameters: dict) -> dict:
    root_errors = _validate_root_parameters(parameters,
                                            [ConfigurationKeysV1.KEY_PATH.value,
                                             ConfigurationKeysV1.KEY_MODE.value,
                                             ConfigurationKeysV1.KEY_METHOD.value])
    if root_errors:
        raise ValidationError(root_errors)

    path = parameters[ConfigurationKeysV1.KEY_PATH.value]
    base_url = f"{urlparse(path).scheme}://{urlparse(path).netloc}"
    parsed_url = urlparse(path)
    endpoint_path = f"{parsed_url.path}?{parsed_url.query}"
    api_config_obj = {"base_url": base_url}

    headers = {}
    for h in parameters.get(ConfigurationKeysV1.KEY_HEADERS.value, []):
        headers[h['key']] = h['value']

    query_parameters = {}
    for p in parameters.get(ConfigurationKeysV1.KEY_ADDITIONAL_PARS.value, []):
        if p['key'] == 'params':
            query_parameters = p['value']

        if p['key'] == 'verify':
            api_config_obj['ssl_verify'] = p['value']

    api_request_obj = {"method": parameters[ConfigurationKeysV1.KEY_METHOD.value],
                       "endpoint_path": endpoint_path,
                       "headers": headers,
                       "query_parameters": query_parameters}

    mode = parameters[ConfigurationKeysV1.KEY_MODE.value]
    json_cfg = parameters.get(ConfigurationKeysV1.KEY_JSON_DATA_CFG.value)
    json_mapping_obj = None
    if json_cfg:
        delimiter = json_cfg.get(ConfigurationKeysV1.KEY_DELIMITER.value, '_')
        infer_types = json_cfg.get(ConfigurationKeysV1.KEY_INFER_TYPES.value, False)
        chunksize = json_cfg.get(ConfigurationKeysV1.KEY_CHUNK_SIZE.value, 100)
        data_wrapper = json_cfg.get(ConfigurationKeysV1.KEY_REQUEST_DATA_WRAPPER.value, '')
        column_names = json_cfg.get(ConfigurationKeysV1.KEY_NAMES_OVERRIDE.value, {})
        column_types = json_cfg.get(ConfigurationKeysV1.KEY_COLUMN_TYPES.value, [])

        json_mapping_obj = {"nesting_delimiter": delimiter,
                            "chunk_size": chunksize,
                            "column_data_types": {"autodetect": infer_types,
                                                  "datatype_override": column_types},
                            "request_data_wrapper": data_wrapper,
                            "column_names_override": column_names}

    iteration_columns = parameters.get(ConfigurationKeysV1.KEY_ITERATION_MODE.value, {}).get(
        ConfigurationKeysV1.KEY_ITERATION_PAR_COLUMNS.value, [])
    req_content_obj = {"content_type": mode,
                       "json_mapping": json_mapping_obj,
                       "iterate_by_columns": iteration_columns}

    user_parameters = parameters.get(ConfigurationKeysV1.KEY_USER_PARS.value) or {}

    new_configuration = {"api": api_config_obj,
                         "user_parameters": user_parameters,
                         "request_parameters": api_request_obj,
                         "request_content": req_content_obj}

    return new_configuration


def validate_required_parameters(config_object, name: str, config_fields: dict) -> str:
    required_fields = get_dataclass_required_params(config_object)
    missing_fields = []
    for key in required_fields:
        if key not in config_fields:
            missing_fields.append(key)
    error = ''
    if missing_fields:
        error = f'Object "{name}" is missing following required fields: {missing_fields}'
    return error


class ValidationError(Exception):
    pass


def _validate_root_parameters(parameters: dict, required_parameters: List[str]):
    missing_fields = []
    for key in required_parameters:
        if key not in parameters:
            missing_fields.append(key)
    error = ''
    if missing_fields:
        error = f'Configuration is missing following required fields: {missing_fields}'
    return error


def validate_configuration_v2(configuration_parameters: dict):
    """
    Validate configuration parameters
    Args:
        configuration_parameters: dict: configuration parameters

    Raises: ValidationError

    """
    root_errors = _validate_root_parameters(configuration_parameters, ['api', 'request_content', 'request_parameters'])
    if root_errors:
        raise ValidationError(root_errors)

    api_config = configuration_parameters['api']
    request_parameters = configuration_parameters['request_parameters']
    request_content = configuration_parameters['request_content']

    # validate
    validation_errors = [validate_required_parameters(ApiConfig, 'api', api_config),
                         validate_required_parameters(ApiRequest, 'request_parameters', request_parameters),
                         validate_required_parameters(RequestContent, 'request_content', request_content)]
    # TODO: validate authentication

    json_mapping = request_content.get('json_mapping')
    if request_content['content_type'] in ['JSON', 'JSON_URL_ENCODED'] and not json_mapping:
        validation_errors.append(
            f"The 'json_mapping' configuration is required in mode {request_content['content_type']}")

    if request_content.get('json_mapping'):
        validation_errors.append(
            validate_required_parameters(JsonMapping, 'json_mapping', request_content['json_mapping']))

    # remove empty
    validation_errors = [e for e in validation_errors if e]
    if validation_errors:
        errors_string = '\n'.join(validation_errors)
        raise ValidationError(
            f"Some required parameters fields are missing: {errors_string}")


def _handle_kbc_error_converting_objects(configuration: WriterConfiguration):
    """
    INPLACE Fixes internal KBC bug old as time itself.
    Args:
        configuration:

    Returns:

    """
    if isinstance(configuration.user_parameters, list):
        configuration.user_parameters = {}

    if configuration.request_parameters and isinstance(configuration.request_parameters.query_parameters, list):
        configuration.request_parameters.query_parameters = {}

    if configuration.request_parameters and isinstance(configuration.request_parameters.headers, list):
        configuration.request_parameters.headers = {}

    if configuration.api and isinstance(configuration.api.default_headers, list):
        configuration.api.default_headers = {}

    if configuration.request_content.json_mapping and isinstance(
            configuration.request_content.json_mapping.column_names_override, list):
        configuration.request_content.json_mapping.column_names_override = {}


def build_configuration(configuration_parameters: dict) -> WriterConfiguration:
    if _is_v2_config(configuration_parameters):
        configuration_parameters = convert_to_v2(configuration_parameters)

    validate_configuration_v2(configuration_parameters)

    api_config_pars = configuration_parameters['api']
    user_parameters = configuration_parameters['user_parameters'] or {}
    request_parameters = configuration_parameters['request_parameters']
    request_content = configuration_parameters['request_content']

    api_config: ApiConfig = build_dataclass_from_dict(ApiConfig, api_config_pars)
    if api_config_pars.get('authentication'):
        api_config.authentication = build_dataclass_from_dict(Authentication, api_config_pars['authentication'])

    retry_config = build_dataclass_from_dict(RetryConfig, api_config_pars.get('retry_config', {}))
    api_config.retry_config = retry_config
    # Request options
    api_request = build_dataclass_from_dict(ApiRequest, request_parameters)

    json_mapping_pars = request_content.get('json_mapping')
    if json_mapping_pars:
        json_mapping_pars['column_data_types'] = build_dataclass_from_dict(ColumnDataTypes,
                                                                           json_mapping_pars['column_data_types'])
        request_content['json_mapping'] = build_dataclass_from_dict(JsonMapping, json_mapping_pars)

    content = build_dataclass_from_dict(RequestContent, request_content)

    result_config = WriterConfiguration(api=api_config, request_parameters=api_request, request_content=content,
                                        user_parameters=user_parameters)
    _handle_kbc_error_converting_objects(result_config)
    return result_config


class ConfigHelpers:

    def __init__(self):
        self.user_functions = UserFunctions()

    def fill_in_user_parameters(self, conf_objects: dict, user_param: dict,
                                evaluate_conf_objects_functions: bool = True):
        """
        This method replaces user parameter references via attr + parses functions inside user parameters,
        evaluates them and fills in the resulting values

        Args:
            conf_objects: Configuration that contains the references via {"attr": "key"} to user parameters or function
                            definitions
            user_param: User parameters that are used to fill in the values

        Returns:

        """
        # time references
        conf_objects = self.fill_in_time_references(conf_objects)
        user_param = self.fill_in_time_references(user_param)
        # convert to string minified
        steps_string = json.dumps(conf_objects, separators=(',', ':'))
        # dirty and ugly replace
        for key in user_param:
            if isinstance(user_param[key], dict):
                # in case the parameter is function, validate, execute and replace value with result
                res = self.perform_custom_function(key, user_param[key], user_param)
                user_param[key] = res

            lookup_str = '{"attr":"' + key + '"}'
            steps_string = steps_string.replace(lookup_str, '"' + str(user_param[key]) + '"')
        new_steps = json.loads(steps_string)
        non_matched = nested_lookup('attr', new_steps)

        if evaluate_conf_objects_functions:
            for key in new_steps:
                if isinstance(new_steps[key], dict):
                    # in case the parameter is function, validate, execute and replace value with result
                    res = self.perform_custom_function(key, new_steps[key], user_param)
                    new_steps[key] = res

        if non_matched:
            raise ValueError(
                'Some user attributes [{}] specified in parameters '
                'are not present in "user_parameters" json_path.'.format(non_matched))
        return new_steps

    @staticmethod
    def fill_in_time_references(conf_objects: dict):
        """
        This method replaces user parameter references via attr + parses functions inside user parameters,
        evaluates them and fills in the resulting values

        Args:
            conf_objects: Configuration that contains the references via {"attr": "key"} to user parameters or function
                            definitions

        Returns:

        """
        # convert to string minified
        steps_string = json.dumps(conf_objects, separators=(',', ':'))
        # dirty and ugly replace

        new_cfg_str = steps_string.replace('{"time":"currentStart"}', f'{int(time.time())}')
        new_cfg_str = new_cfg_str.replace('{"time":"previousStart"}', f'{int(time.time())}')
        new_config = json.loads(new_cfg_str)
        return new_config

    def perform_custom_function(self, key: str, function_cfg: dict, user_params: dict):
        """
        Perform custom function recursively (may be nested)
        Args:
            key: key of the user parameter wher the function is
            function_cfg: conf of the function
            user_params:

        Returns:

        """
        function_cfg = self.fill_in_time_references(function_cfg)
        if not isinstance(function_cfg, dict):
            # in case the function was evaluated as time
            return function_cfg

        elif function_cfg.get('attr'):
            return user_params[function_cfg['attr']]

        if not function_cfg.get('function'):
            for key in function_cfg:
                function_cfg[key] = self.perform_custom_function(key, function_cfg[key], user_params)

        new_args = []
        if function_cfg.get('args'):
            for arg in function_cfg.get('args'):
                if isinstance(arg, dict):
                    arg = self.perform_custom_function(key, arg, user_params)
                new_args.append(arg)
            function_cfg['args'] = new_args
        if isinstance(function_cfg, dict) and not function_cfg.get('function'):
            return function_cfg
        return self.user_functions.execute_function(function_cfg['function'], *function_cfg.get('args', []))


class AuthMethodConverter:
    @classmethod
    def convert_login(cls, config_parameters) -> dict:
        method_mapping = {'GET': 'GET', 'POST': 'POST', 'FORM': 'POST'}
        helpers = ConfigHelpers()
        login_request: dict = config_parameters.api.authentication.parameters.get("loginRequest", {})
        api_request: dict = config_parameters.api.authentication.parameters.get("apiRequest", {})
        # evaluate functions and user parameters
        user_parameters = build_user_parameters(config_parameters)
        user_parameters = helpers.fill_in_user_parameters(user_parameters, user_parameters)
        login_request_eval = helpers.fill_in_user_parameters(login_request, user_parameters)
        # the function evaluation is left for the Auth method because of the response placeholder
        api_request_eval = helpers.fill_in_user_parameters(api_request, user_parameters, False)

        if not login_request:
            raise ValueError('loginRequest configuration not found in the Login Authentication configuration')

        login_endpoint: str = login_request_eval.get('endpoint')
        login_url = urljoin(config_parameters.api.base_url, login_endpoint)

        method = login_request_eval.get('method', 'GET')

        login_request_content: RequestContent = build_request_content(method, login_request_eval.get('params', {}))

        try:
            result_method: str = method_mapping[login_request_eval.get('method', 'GET').upper()]
        except KeyError:
            raise ValueError(f'Unsupported method: {login_request_eval.get("method")}')

        login_query_parameters: dict = login_request_content.query_parameters
        login_headers: dict = login_request_eval.get('headers', {})
        api_request_headers: dict = api_request_eval.get('headers', {})
        api_request_query_parameters: dict = api_request_eval.get('query', {})

        parameters = {'login_endpoint': login_url,
                      'method': result_method,
                      'login_query_parameters': login_query_parameters,
                      'login_headers': login_headers,
                      'login_query_body': login_request_content.body,
                      'login_content_type': login_request_content.content_type.value,
                      'api_request_headers': api_request_headers,
                      'api_request_query_parameters': api_request_query_parameters}

        return parameters


def build_user_parameters(configuration: dict) -> dict:
    """
    Build user parameters from configuration
    Args:
        configuration: Configuration in v2 format

    Returns: User parameters

    """
    config_excluded_keys = ['__AUTH_METHOD', '__NAME', '#__BEARER_TOKEN', 'jobs', 'outputBucket', 'incrementalOutput',
                            'http', 'debug', 'mappings', ' #username', '#password', 'userData']
    user_parameters = {}
    for key, value in configuration.user_parameters.items():
        if key not in config_excluded_keys:
            user_parameters[key] = value
    return user_parameters


def build_request_content(method: Literal['GET', 'POST', 'FORM'], params: dict) -> RequestContent:
    match method:
        case 'GET':
            request_content = RequestContent(ContentType.none, query_parameters=params)
        case 'POST':
            request_content = RequestContent(ContentType.json,
                                             body=params)
        case 'FORM':
            request_content = RequestContent(ContentType.form,
                                             body=params)
        case _:
            raise ValueError(f'Unsupported method: {method}')
    return request_content
