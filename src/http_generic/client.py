from typing import Tuple, Dict

from keboola.http_client import HttpClient

from http_generic.auth import AuthMethodBase


class GenericHttpClient(HttpClient):

    def __init__(self, base_url: str,
                 default_http_header: Dict = None,
                 default_params: Dict = None,
                 auth_method: AuthMethodBase = None,
                 max_retries: int = 10,
                 backoff_factor: float = 0.3,
                 status_forcelist: Tuple[int, ...] = (500, 502, 504)
                 ):
        super().__init__(base_url=base_url, max_retries=max_retries, backoff_factor=backoff_factor,
                         status_forcelist=status_forcelist,
                         default_http_header=default_http_header, default_params=default_params)

        self._auth_method = auth_method

    def login(self):
        """
        Perform login based on auth method

        """
        # perform login
        self._auth = self._auth_method.login()

    def send_request(self, method, url, **kwargs):
        self._request_raw(method=method, endpoint_path=url, is_absolute_path=True, **kwargs)
