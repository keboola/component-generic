import difflib
import gzip
import os
import tempfile
from io import BufferedReader, BytesIO


def query_param_matcher(params):
    """
    Matcher to match 'params' argument in request
    :param params: (dict), same as provided to request
    :return: (func) matcher
    """

    def match(request):
        request_params = request.params
        valid = (
            params is None
            if request_params is None
            else sorted(params.items()) == sorted(request_params.items())
        )

        if not valid:
            return False, "%s doesn't match %s" % (
                sorted(request_params.items()),
                sorted(params.items()),
            )

        return valid, ""

    return match


def binary_payload_matcher(params):
    """
    Matches JSON encoded data
    :param params: (str) path to source binary file
    :return: (func) matcher
    """

    def _compare_files(path1, path2):
        with open(path1, 'r') as in1, open(path2, 'r') as in2:
            body1 = in1.read()
            body2 = in2.read()
        errors = difflib.context_diff(body1, body2)  # set the compare output to a variable

        return len(list(errors)) == 0

    def match(request):
        request_body = request.body
        result = tempfile.mktemp()
        valid = False
        try:
            if isinstance(request_body, BufferedReader):
                with open(result, 'wb+') as out:
                    for chunk in request_body:
                        out.write(chunk)
                valid = _compare_files(result, params)
            # compare
            if not valid:
                return False, "The binary files do not match!"

            return valid, ""
        except Exception as e:
            return False, f"Cannot parse request.content. {e}"
        finally:
            request_body.close()
            os.remove(result)

    return match


def binary_gz_payload_matcher(params):
    """
    Matches JSON encoded data
    :param params: (str) path to source binary file
    :return: (func) matcher
    """

    def _compare_files(decompressed_result, path2):
        with open(path2, 'r') as inp:
            body2 = inp.read()
        errors = difflib.context_diff(decompressed_result, body2)  # set the compare output to a variable

        return len(list(errors)) == 0

    def match(request):
        request_body = request.body
        result = tempfile.mktemp()
        valid = False
        try:
            if isinstance(request_body, BufferedReader):
                with open(result, 'wb+') as out:
                    for chunk in request_body:
                        out.write(chunk)
                with open(result, 'rb') as gz:
                    decompressed = gzip.decompress(gz.read())
                valid = _compare_files(decompressed.decode('utf-8'), params)
            # compare
            if not valid:
                return False, "The binary files do not match!"

            return valid, ""
        except Exception as e:
            return False, f"Cannot parse request.content. {e}"
        finally:
            request_body.close()
            os.remove(result)

    return match


def binary_payload_multi_matcher_to_string(strings_to_match):
    """
    Matches JSON encoded data
    :param string_to_match: (dict[str]) string to match, per url
    :return: (func) matcher
    """

    def _compare_files(decompressed_result, path2):
        with open(path2, 'r') as inp:
            body2 = inp.read()
        errors = difflib.context_diff(decompressed_result, body2)  # set the compare output to a variable

        return len(list(errors)) == 0, f"Expected content: {decompressed_result}; vs. received: {body2} "

    def match(request):
        request_body = request.body
        result = tempfile.mktemp()
        valid = False
        errors = ""
        try:
            if isinstance(request_body, (BufferedReader, BytesIO)):
                with open(result, 'wb+') as out:
                    for chunk in request_body:
                        out.write(chunk)
                valid, errors = _compare_files(strings_to_match[request.url.split('?')[0]], result)
                os.remove(result)
            # compare
            if not valid:
                return False, f"The binary files do not match. " \
                              f"{errors}! "

            return valid, ""
        except Exception as e:
            return False, f"Cannot parse request.content. {e}"
        finally:
            request_body.close()

    return match
