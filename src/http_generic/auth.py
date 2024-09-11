import inspect
from abc import ABC, abstractmethod

from requests.auth import AuthBase, HTTPBasicAuth
from typing import Callable, Union, Dict, Literal
from urllib.parse import urlencode, urljoin
import requests
import json
from placeholders_utils import get_data_from_path
import re

from configuration import ContentType, ConfigHelpers, RequestContent


class AuthBuilderError(Exception):
    pass


class AuthMethodBase(ABC):
    """
    Base class to implement the authentication method. To mark secret constructor parameters prefix them with __
    e.g. __init__(self, username, __password)
    """

    @abstractmethod
    def login(self):
        """
        Perform steps to login and returns requests.aut.AuthBase callable that modifies the request.

        """
        pass


class AuthMethodBuilder:

    @classmethod
    def build(cls, method_name: str, **parameters):
        """

        Args:
            method_name:
            **parameters: dictionary of named parameters. Note that parameters prefixed # will be converted to __

        Returns:

        """
        supported_actions = cls.get_methods()

        if method_name not in list(supported_actions.keys()):
            raise AuthBuilderError(f'{method_name} is not supported auth method, '
                                   f'supported values are: [{list(supported_actions.keys())}]')

        parameters = cls._convert_secret_parameters(supported_actions[method_name], **parameters)

        cls._validate_method_arguments(supported_actions[method_name], **parameters)

        return supported_actions[method_name](**parameters)

    @staticmethod
    def _validate_method_arguments(method_obj: object, **args):
        class_prefix = f"_{method_obj.__name__}__"
        arguments = [p for p in inspect.signature(method_obj.__init__).parameters if p != 'self']

        missing_arguments = []
        for p in arguments:
            if p not in args:
                missing_arguments.append(p.replace(class_prefix, '#'))
        if missing_arguments:
            raise AuthBuilderError(f'Some arguments of method {method_obj.__name__} are missing: {missing_arguments}')

    @staticmethod
    def _convert_secret_parameters(method_obj: object, **parameters):
        new_parameters = {}
        for p in parameters:
            new_parameters[p.replace('#', f'_{method_obj.__name__}__')] = parameters[p]
        return new_parameters

    @staticmethod
    def get_methods() -> Dict[str, Callable]:
        supported_actions = {}
        for c in AuthMethodBase.__subclasses__():
            supported_actions[c.__name__] = c
        return supported_actions

    @classmethod
    def get_supported_methods(cls):
        return list(cls.get_methods().keys())

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
        api_request_query_parameters: dict = api_request_eval.get('query_parameters', {})

        parameters = {'login_endpoint': login_url,
                      'method': result_method,
                      'login_query_parameters': login_query_parameters,
                      'login_headers': login_headers,
                      'login_query_body': login_request_content.body,
                      'login_content_type': login_request_content.content_type.value,
                      'api_request_headers': api_request_headers,
                      'api_request_query_parameters': api_request_query_parameters}

        return parameters


# ########### SUPPORTED AUTHENTICATION METHODS

class BasicHttp(AuthMethodBase):

    def __init__(self, username, __password):
        self.username = username
        self.password = __password

    def login(self) -> Union[AuthBase, Callable]:
        return HTTPBasicAuth(username=self.username, password=self.password)

    def __eq__(self, other):
        return all([
            self.username == getattr(other, 'username', None),
            self.password == getattr(other, 'password', None)
        ])


class BearerToken(AuthMethodBase, AuthBase):

    def __init__(self, __token):
        self.token = __token

    def login(self) -> Union[AuthBase, Callable]:
        return self

    def __eq__(self, other):
        return all([
            self.token == getattr(other, 'token', None)
        ])

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers['authorization'] = f"Bearer {self.token}"
        return r


class ApiKey(AuthMethodBase, AuthBase):
    def get_secrets(self) -> list[str]:
        return [self.token]

    def __init__(self, key: str, __token: str, position: str):
        self.token = __token
        self.key = key
        self.position = position

    def login(self) -> Union[AuthBase, Callable]:
        return self

    def __eq__(self, other):
        return all([
            self.token == getattr(other, 'token', None)
        ])

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        if self.position == 'headers':
            r.headers[self.key] = f"{self.token}"

        elif self.position == 'query':
            r.url = f"{r.url}?{urlencode({self.key: self.token})}"
        else:
            raise AuthBuilderError(f"Unsupported position {self.position} for API Key auth method")
        return r


class Login(AuthMethodBase, AuthBase):

    def __init__(self, login_endpoint: str, method: str = 'GET',
                 login_query_parameters: dict = None,
                 login_query_body=None,
                 login_content_type: str = ContentType.json.value,
                 login_headers: dict = None,
                 api_request_headers: dict = None, api_request_query_parameters: dict = None):
        """

        Args:
            login_endpoint:
            method:
            login_query_parameters:
            login_headers:
            api_request_headers:
            api_request_query_parameters:
        """
        self.login_endpoint = login_endpoint
        self.method = method
        self.login_query_parameters = login_query_parameters or {}
        self.login_query_body = login_query_body
        self.login_content_type = ContentType(login_content_type)
        self.login_headers = login_headers or {}
        self.api_request_headers = api_request_headers or {}
        self.api_request_query_parameters = api_request_query_parameters or {}

    @classmethod
    def _retrieve_response_placeholders(cls, request_object: dict, separator: str = '.', current_path: str = '') -> \
            list[str]:
        """
        Recursively retreive all values that contain object with key `response` and return it's value and json path
        Args:
            request_object:

        Returns:

        """
        request_object_str = json.dumps(request_object, separators=(',', ':'))
        lookup_str_func = r'"response":"([^"]*)"'
        # Use re.search to find the pattern in your_string
        matches = re.findall(lookup_str_func, request_object_str)

        return matches

    def _replace_placeholders_with_response(self, response_data: dict, source_object_params: dict) -> dict:
        """
        Replace placeholders in source_object_params with values from response_data
        Args:
            response_data:
            source_object_params:

        Returns:

        """
        response_placeholders = self._retrieve_response_placeholders(source_object_params)
        source_object_params_str = json.dumps(source_object_params, separators=(',', ':'))
        for placeholder in response_placeholders:
            lookup_str = '{"response":"' + placeholder + '"}'
            value_to_replace = get_data_from_path(placeholder, response_data, separator='.', strict=False)
            source_object_params_str = source_object_params_str.replace(lookup_str, '"' + value_to_replace + '"')
        return json.loads(source_object_params_str)

    def login(self) -> Union[AuthBase, Callable]:
        request_parameters = {}

        if self.login_content_type == ContentType.json:
            request_parameters['json'] = self.login_query_body
        elif self.login_content_type == ContentType.form:
            request_parameters['data'] = self.login_query_body

        response = requests.request(self.method, self.login_endpoint, params=self.login_query_parameters,
                                    headers=self.login_headers,
                                    **request_parameters)

        response.raise_for_status()

        self.api_request_headers = self._replace_placeholders_with_response(response.json(), self.api_request_headers)
        self.api_request_query_parameters = self._replace_placeholders_with_response(response.json(),
                                                                                     self.api_request_query_parameters)
        cfg_helpers = ConfigHelpers()
        self.api_request_headers = cfg_helpers.fill_in_user_parameters(self.api_request_headers, {},
                                                                       True)
        self.api_request_query_parameters = cfg_helpers.fill_in_user_parameters(self.api_request_query_parameters,
                                                                                {},
                                                                                True)
        return self

    def get_secrets(self) -> list[str]:
        secrets = []
        for key, value in self.api_request_query_parameters.items():
            secrets.append(value)

        for key, value in self.api_request_headers.items():
            secrets.append(value)

        return secrets

    def __call__(self, r):

        r.url = f"{r.url}"
        if self.api_request_query_parameters:
            r.url = f"{r.url}?{urlencode(self.api_request_query_parameters)}"
        r.headers.update(self.api_request_headers)
        return r


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
