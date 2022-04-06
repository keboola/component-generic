import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple
from urllib.parse import urlparse

from keboola.component.dao import build_dataclass_from_dict


@dataclass
class SubscriptableDataclass:
    """
    Helper class to make dataclasses subscriptable
    """

    def __getitem__(self, index):
        return getattr(self, index)

    def __setitem__(self, key, value):
        return setattr(self, key, value)


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


def validate_configuration_v2(configuration_parameters: dict):
    """
    Validate configuration parameters
    Args:
        configuration_parameters: dict: configuration parameters

    Raises: ValidationError

    """
    api_config = configuration_parameters['api']
    request_parameters = configuration_parameters['request_parameters']
    request_content = configuration_parameters['request_content']

    # validate
    validation_errors = []
    validation_errors.append(validate_required_parameters(ApiConfig, 'api', api_config))
    # TODO: validate authentication
    validation_errors.append(
        validate_required_parameters(ApiRequest, 'request_parameters', request_parameters))
    validation_errors.append(
        validate_required_parameters(RequestContent, 'request_content', request_content))

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

    return WriterConfiguration(api=api_config, request_parameters=api_request, request_content=content,
                               user_parameters=user_parameters)
