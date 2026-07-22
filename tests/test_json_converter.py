import csv
import io
import json
import unittest

from keboola.component import UserException

from json_converter import JsonConverter


class TestJsonConverterDataWrapper(unittest.TestCase):
    """Regression tests for the request_data_wrapper handling in JsonConverter."""

    @staticmethod
    def _reader(csv_text):
        return csv.reader(io.StringIO(csv_text), lineterminator="\n")

    # --- happy path: behaviour must be unchanged ---

    def test_no_wrapper_returns_data_unchanged(self):
        converter = JsonConverter()
        self.assertEqual({"a": 1}, converter._wrap_json_payload({"a": 1}))

    def test_valid_wrapper_still_wraps_payload(self):
        converter = JsonConverter(data_wrapper='{"root": {{data}}}')
        self.assertEqual({"root": [{"a": 1}]}, converter._wrap_json_payload([{"a": 1}]))

    def test_valid_legacy_wrapper_still_wraps_payload(self):
        # backward compatibility: the legacy [[data]] placeholder must keep working
        converter = JsonConverter(data_wrapper='{"root": [[data]]}')
        self.assertEqual({"root": [{"a": 1}]}, converter._wrap_json_payload([{"a": 1}]))

    def test_valid_wrapper_convert_stream(self):
        converter = JsonConverter(data_wrapper='{"root": {{data}}}')
        chunks = list(converter.convert_stream(self._reader("id,name\n1,keboola\n")))
        self.assertEqual(1, len(chunks))
        self.assertIn("root", chunks[0])

    # --- defensive path: malformed wrapper degrades to a clear UserException ---

    def test_malformed_wrapper_raises_user_exception(self):
        # missing closing brace -> invalid JSON after substitution
        converter = JsonConverter(data_wrapper='{"root": {{data}}')
        with self.assertRaises(UserException):
            converter._wrap_json_payload([{"a": 1}])

    def test_malformed_wrapper_convert_stream_raises_user_exception(self):
        converter = JsonConverter(data_wrapper="not json {{data}}")
        with self.assertRaises(UserException):
            list(converter.convert_stream(self._reader("id,name\n1,keboola\n")))

    def test_malformed_wrapper_does_not_leak_raw_json_decode_error(self):
        converter = JsonConverter(data_wrapper='{"root": {{data}}')
        with self.assertRaises(UserException):
            try:
                converter._wrap_json_payload([{"a": 1}])
            except json.JSONDecodeError:  # pragma: no cover - must not happen anymore
                self.fail("raw json.JSONDecodeError leaked instead of UserException")


if __name__ == "__main__":
    unittest.main()
