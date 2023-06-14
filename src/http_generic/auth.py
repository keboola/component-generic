import inspect
from abc import ABC, abstractmethod
from typing import Callable, Union, Dict

from requests.auth import AuthBase, HTTPBasicAuth

from http_generic.signature import SignatureBase, NoSignature


class AuthBuilderError(Exception):
    pass


class AuthMethodBase(ABC, AuthBase):
    """
    Base class to implement the authentication method. To mark secret constructor parameters prefix them with __
    e.g. __init__(self, username, __password)
    """

    def __init__(self, signature_function: SignatureBase):
        self.signature_function = signature_function

    @abstractmethod
    def login(self):
        """
        Perform steps to login and returns requests.aut.AuthBase callable that modifies the request.

        """
        pass

    def sign_request(self, r):
        """
        Sign request using a defined signature method

        """
        return self.signature_function.sign(r)

    def authorize_request(self, r):
        return r

    def __call__(self, r):
        r = self.authorize_request(r)
        r = self.sign_request(r)
        return r


class AuthMethodBuilder:

    @classmethod
    def build(cls, method_name: str, signature_function: SignatureBase = None, **parameters) -> AuthMethodBase:
        """

        Args:
            signature_function: Request signature function to use as part of authentication
            method_name:
            **parameters: dictionary of named parameters. Note that parameters prefixed # will be converted to __

        Returns:

        """
        if not signature_function:
            signature_function = NoSignature()

        supported_actions = cls.get_methods()

        if method_name not in list(supported_actions.keys()):
            raise AuthBuilderError(f'{method_name} is not supported auth method, '
                                   f'supported values are: [{list(supported_actions.keys())}]')
        parameters = cls._convert_secret_parameters(supported_actions[method_name], **parameters)
        cls._validate_method_arguments(supported_actions[method_name], signature_function=signature_function,
                                       **parameters)

        return supported_actions[method_name](signature_function=signature_function, **parameters)

    @staticmethod
    def _validate_method_arguments(method: object, **args):
        class_prefix = f"_{method.__name__}__"
        arguments = [p for p in inspect.signature(method.__init__).parameters if p != 'self']
        missing_arguments = []
        for p in arguments:
            if p not in args:
                missing_arguments.append(p.replace(class_prefix, '#'))
        if missing_arguments:
            raise AuthBuilderError(f'Some arguments of method {method.__name__} are missing: {missing_arguments}')

    @staticmethod
    def _convert_secret_parameters(method: object, **parameters):
        new_parameters = {}
        for p in parameters:
            new_parameters[p.replace('#', f'_{method.__name__}__')] = parameters[p]
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


# ########### SUPPORTED AUTHENTICATION METHODS
class NoAuthentication(AuthMethodBase):

    def __init__(self, signature_function):
        super(NoAuthentication, self).__init__(signature_function)

    def login(self) -> Union[AuthBase, Callable]:
        return self

    def authorize_request(self, r):
        return r


class BasicHttp(AuthMethodBase):

    def __init__(self, signature_function, username, __password):
        super(BasicHttp, self).__init__(signature_function)
        self.username = username
        self.password = __password

    def login(self) -> Union[AuthBase, Callable]:
        return self

    def authorize_request(self, r):
        return HTTPBasicAuth(username=self.username, password=self.password)(r)

    def __eq__(self, other):
        return all([
            self.username == getattr(other, 'username', None),
            self.password == getattr(other, 'password', None)
        ])


class BearerToken(AuthMethodBase):

    def __init__(self, signature_function, __token):
        super(BearerToken, self).__init__(signature_function)
        self.token = __token

    def login(self) -> Union[AuthBase, Callable]:
        return self

    def authorize_request(self, r):
        r.headers['authorization'] = f"Bearer {self.token}"
        return r

    def __eq__(self, other):
        return all([
            self.token == getattr(other, 'token', None)
        ])

    def __ne__(self, other):
        return not self == other
