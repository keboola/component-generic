import hashlib
import inspect
import json
from abc import ABC, abstractmethod
from typing import Dict, Callable
from urllib.parse import urlparse, parse_qs


class SignatureBuilderError(Exception):
    pass


class SignatureBase(ABC):
    """
    Base class to implement the authentication method. To mark secret constructor parameters prefix them with __
    e.g. __init__(self, username, __password)
    """

    @abstractmethod
    def sign(self, r):
        """
        Perform steps to login and returns requests.aut.AuthBase callable that modifies the request.

        """
        pass


class SignMethodBuilder:

    @classmethod
    def build(cls, method_name: str, **parameters) -> SignatureBase:
        """

        Args:
            method_name:
            **parameters: dictionary of named parameters. Note that parameters prefixed # will be converted to __

        Returns:

        """
        supported_actions = cls.get_methods()

        if method_name not in list(supported_actions.keys()):
            raise SignatureBuilderError(f'{method_name} is not supported signature method, '
                                        f'supported values are: [{list(supported_actions.keys())}]')
        parameters = cls._convert_secret_parameters(supported_actions[method_name], **parameters)
        cls._validate_method_arguments(supported_actions[method_name], **parameters)

        return supported_actions[method_name](**parameters)

    @staticmethod
    def _validate_method_arguments(method: object, **args):
        class_prefix = f"_{method.__name__}__"
        arguments = [p for p in inspect.signature(method.__init__).parameters if p != 'self']
        missing_arguments = []
        for p in arguments:
            if p not in args:
                missing_arguments.append(p.replace(class_prefix, '#'))
        if missing_arguments:
            raise SignatureBuilderError(f'Some arguments of method {method.__name__} are missing: {missing_arguments}')

    @staticmethod
    def _convert_secret_parameters(method: object, **parameters):
        new_parameters = {}
        for p in parameters:
            new_parameters[p.replace('#', f'_{method.__name__}__')] = parameters[p]
        return new_parameters

    @staticmethod
    def get_methods() -> Dict[str, Callable]:
        supported_actions = {}
        for c in SignatureBase.__subclasses__():
            supported_actions[c.__name__] = c
        return supported_actions

    @classmethod
    def get_supported_methods(cls):
        return list(cls.get_methods().keys())


# ##### SIGNATURE METHODS

class NoSignature(SignatureBase):
    def sign(self, r):
        return r


class HMAC(SignatureBase):
    def __init__(self, concat_values: list, key='sig', hash_function='md5', location='json_body'):
        self._concat_values = concat_values
        self._sig_key = key
        self._sys_key_mapping = {'$body': '', '$request_parameters': {}}

    def _get_url_params(self, r) -> dict:
        query = urlparse(r.url).query
        query_parsed = parse_qs(query)
        return query_parsed

    def _get_dict_values_sorted(self, parameters: dict):

        keys = list(parameters.keys())
        keys.sort()
        sorted_values = [parameters[i][0] for i in keys]
        return ''.join(sorted_values)

    def concat_data(self, r):
        body = ''
        if r.headers['content-type'].lower() == 'application/json':
            body = r.body.decode('utf-8')
        self._sys_key_mapping['$body'] = body
        self._sys_key_mapping['$request_parameters'] = self._get_dict_values_sorted(self._get_url_params(r))

        result_key = []
        for c in self._concat_values:
            if c in self._sys_key_mapping:
                result_key.append(self._sys_key_mapping[c])
            else:
                result_key.append(c)
        return ''.join(result_key)

    def sign(self, r):
        concat_data = self.concat_data(r)
        hashed = hashlib.md5(concat_data.encode()).hexdigest()
        body = json.loads(r.body.decode('utf-8'))
        body[self._sig_key] = hashed
        r.prepare_body(None, None, body)

        return r
