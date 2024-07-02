import json
import logging
import sys
from typing import List, Dict, Optional, Generator

from csv2json.hone_csv2json import Csv2JsonConverter


class JsonConverter:

    def __init__(self, nesting_delimiter: str = '__',
                 chunk_size: Optional[int] = None,
                 infer_data_types=True,
                 column_data_types: Optional[List[Dict[str, str]]] = None,
                 column_name_override: Optional[dict] = None,
                 data_wrapper: Optional[str] = None):

        self.nesting_delimiter = nesting_delimiter
        self.chunk_size = chunk_size or sys.maxsize
        self.infer_data_types = infer_data_types
        self.column_data_types = column_data_types or []
        self.data_wrapper = data_wrapper
        self.column_name_override = column_name_override or {}

    def convert_stream(self, reader) -> Generator[dict, None, None]:
        header = next(reader, None)
        converter = Csv2JsonConverter(header, delimiter=self.nesting_delimiter)
        # fetch first row
        row = next(reader, None)

        if not row:
            logging.warning('The file is empty!')

        while row:  # outer loop, create chunks
            continue_it = True
            i = 0
            json_string = '[' if self.chunk_size > 1 else ''
            while continue_it:
                i += 1

                # for infinity values, we need to replace them with a special string
                row = [f'__{item}__' if self._is_infinity(item) else item for item in row]

                result = converter.convert_row(row=row,
                                               coltypes=self.column_data_types,
                                               delimit=self.nesting_delimiter,
                                               colname_override=self.column_name_override,
                                               infer_undefined=self.infer_data_types)

                # and for infinity values replace back
                for key, value in result[0].items():
                    if self._is_infinity(value, True):
                        result[0][key] = value.replace('__', '')

                json_string += json.dumps(result[0])
                row = next(reader, None)

                if not row or (self.chunk_size and i >= self.chunk_size):
                    continue_it = False

                if continue_it:
                    json_string += ','

            json_string += ']' if self.chunk_size > 1 else ''
            data = json.loads(json_string)
            data = self._wrap_json_payload(data)
            yield data

    @staticmethod
    def _is_infinity(value, reverse=False):
        i_keys = ['infinity', '-infinity', 'inf', '-inf']
        l_value = str(value).lower()
        for key in i_keys:
            if reverse:
                key = f'__{key}__'
            if l_value == key:
                return True
        return False

    def _wrap_json_payload(self, data: dict):
        if not self.data_wrapper:
            return data
        # backward compatibility
        res = self.data_wrapper.replace('{{data}}', json.dumps(data))
        res = res.replace('[[data]]', json.dumps(data))
        return json.loads(res)
