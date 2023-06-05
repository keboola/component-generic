from typing import Tuple, Dict

import csv
from datetime import datetime
import re
import logging
import requests
from keboola.component import UserException
from keboola.http_client import HttpClient
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, InvalidJSONError, ConnectionError
from urllib3 import Retry

from http_generic.auth import AuthMethodBase


class GenericHttpClient(HttpClient):

    def __init__(self, base_url: str,
                 default_http_header: Dict = None,
                 default_params: Dict = None,
                 auth_method: AuthMethodBase = None,
                 max_retries: int = 10,
                 backoff_factor: float = 0.3,
                 status_forcelist: Tuple[int, ...] = (500, 502, 504),
                 log_file_path: str = None,
                 debug: bool = False
                 ):
        super().__init__(base_url=base_url, max_retries=max_retries, backoff_factor=backoff_factor,
                         status_forcelist=status_forcelist,
                         default_http_header=default_http_header, default_params=default_params)

        self._auth_method = auth_method

        self._log_file_path = log_file_path
        if self._log_file_path:
            self.to_csv = True
        else:
            self.to_csv = False

        self._debug = debug

    def login(self):
        """
        Perform login based on auth method

        """
        # perform login
        if self._auth_method:
            self._auth = self._auth_method.login()

    def send_request(self, method, endpoint_path, **kwargs):
        try:
            self.log(f"Request method: {method}")
            self.log(f"Endpoint path: {endpoint_path}")

            headers = kwargs.get('headers')
            headers_str = str(headers) if headers else None
            self.mask_headers(headers_str) if headers_str else None
            self.log(f"Request headers: {headers_str}", to_debug=self._debug)

            self.log(f"Request body: {kwargs.get('data') if kwargs.get('data') else kwargs.get('json')}")

            resp = self._request_raw(method=method, endpoint_path=endpoint_path, is_absolute_path=False, **kwargs)
            resp.raise_for_status()

            self.log(f"Response body received: {resp.text}", to_debug=self._debug)

        except HTTPError as e:
            if e.response.status_code in self.status_forcelist:
                message = f'Request "{method}: {endpoint_path}" failed, too many retries. ' \
                          f'Status Code: {e.response.status_code}. Response: {e.response.text}'
            else:
                message = f'Request "{method}: {endpoint_path}" failed with non-retryable error. ' \
                          f'Status Code: {e.response.status_code}. Response: {e.response.text}'
            raise UserException(message) from e
        except InvalidJSONError:
            message = f'Request "{method}: {endpoint_path}" failed. The JSON payload is invalid (more in detail). ' \
                      f'Verify the datatype conversion.'
            data = kwargs.get('data') or kwargs.get('json')
            raise UserException(message, data)
        except ConnectionError as e:
            message = f'Request "{method}: {endpoint_path}" failed with the following error: {e}'
            raise UserException(message) from e

    def build_url(self, base_url, endpoint_path):
        self.base_url = base_url
        return self._build_url(endpoint_path)

    # override to continue on retry error
    def _requests_retry_session(self, session=None):
        session = session or requests.Session()
        retry = Retry(
            total=self.max_retries,
            read=self.max_retries,
            connect=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods=self.allowed_methods,
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def log(self, msg: str, to_debug: bool = False):
        if to_debug:
            logging.debug(msg)

        if self.to_csv:
            _msg = {
                "utc_ts":  str(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
                "entry": str(msg)

            }
            self.save_dict_to_csv(_msg)

    def save_dict_to_csv(self, data_dict):
        fieldnames = list(data_dict.keys())
        with open(self._log_file_path, 'a', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writerow(data_dict)

    @staticmethod
    def mask_headers(headers: str):
        patterns = [
            r"Bearer\s+\w+",  # Bearer Tokens
            r"password\s*=\s*\w+",  # Passwords
            r"api_key\s*=\s*\w+",  # API Keys
            r"access_token\s*=\s*\w+",  # Access Tokens
            r"client_secret\s*=\s*\w+",  # Client Secrets
            r"authorization_code\s*=\s*\w+",  # Authorization Codes
            r"refresh_token\s*=\s*\w+",  # Refresh Tokens
            r"oauth_secret\s*=\s*\w+"  # OAuth Secrets
        ]

        for pattern in patterns:
            headers = re.sub(pattern, '****', headers)

        return headers
