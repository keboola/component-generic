from abc import ABC, abstractmethod
from typing import Callable, Union

from requests.auth import AuthBase, HTTPBasicAuth


class AuthMethodBase(ABC):

    @abstractmethod
    def login(self):
        """
        Perform steps to login and returns requests.aut.AuthBase callable that modifies the request.

        """
        pass


class AuthMethodBuilder:

    @classmethod
    def build(cls, method_name, **parameters):
        # TODO: validate parameters based on type
        supported_actions = cls.get_methods_actions()
        if method_name not in list(supported_actions.keys()):
            raise ValueError(f'{method_name} is not supported auth method, '
                             f'supported values are: [{list(supported_actions.keys())}]')

        return supported_actions[method_name](**parameters)

    @staticmethod
    def get_methods_actions():
        supported_actions = {}
        for c in AuthMethodBase.__subclasses__():
            supported_actions[c.__name__] = c
        return supported_actions


# ########### SUPPORTED AUTHENTICATION METHODS

class BasicHttp(AuthMethodBase):

    def __init__(self, username, password):
        self.__username = username
        self.__password = password

    def login(self) -> Union[AuthBase, Callable]:
        return HTTPBasicAuth(username=self.__username, password=self.__password)
