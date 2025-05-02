import base64
import hashlib

import keboola.utils as kbcutils


class UserFunctions:
    """
    Custom function to be used in configruation
    """

    def validate_function_name(self, function_name):
        supp_functions = self.get_supported_functions()
        if function_name not in self.get_supported_functions():
            raise ValueError(
                f"Specified user function [{function_name}] is not supported! Supported functions are {supp_functions}"
            )

    @classmethod
    def get_supported_functions(cls):
        return [
            method_name
            for method_name in dir(cls)
            if callable(getattr(cls, method_name))
            and not method_name.startswith("__")
            and method_name not in ["validate_function_name", "get_supported_functions", "execute_function"]
        ]

    def execute_function(self, function_name, *pars):
        self.validate_function_name(function_name)
        return getattr(UserFunctions, function_name)(self, *pars)

    # ############## USER FUNCTIONS
    def string_to_date(self, date_string, date_format="%Y-%m-%d"):
        start_date, end_date = kbcutils.parse_datetime_interval(date_string, date_string)
        return start_date.strftime(date_format)

    def concat(self, *args):
        return "".join(args)

    def base64_encode(self, s):
        return base64.b64encode(s.encode("utf-8")).decode("utf-8")

    def md5_encode(self, s):
        return hashlib.md5(s.encode("utf-8")).hexdigest()
