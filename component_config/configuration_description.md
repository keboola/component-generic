## Data Transmission Methods

The data can be sent in two ways:

1. **Send all content at once** - either as binary or JSON in chunks.
2. **[Iterate](/extend/generic-writer/configuration/#iterate-by-columns) through each row** - where data is sent in
   iterations based on the input data. By default, **1 row = 1 iteration**.
    - This allows dynamic endpoint changes using placeholders, e.g., `www.example.com/api/user/{{id}}`.
    - Enables sending data with different user parameters present in the input table.

### Supported Content Types

- `JSON` - The input table is converted into JSON (see `json_mapping`) and sent as `application/json`.
  See [example 001](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/001-simple-json/).
- `JSON_URL_ENCODED` - The input table is converted into JSON and sent as `application/x-www-form-urlencoded`.
  See [example 021](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/021-simple-json-url-encoded-form/).
- `BINARY` - The input table is sent as binary data (similar to `curl --data-binary`).
  See an [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_simple/).
- `BINARY-GZ` - The input is sent as gzipped binary data.
  See an [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_gz/).
- `EMPTY_REQUEST` - Sends empty requests, usefull for triggerring webhooks, DELETE calls, etc.
    - The number of requests matches the number of rows in the input.
    - Works well with `iterate_by_columns` enabled to trigger multiple endpoints.
    - See [example 022](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/022-empty-request-iterations-delete/).

### Example Configuration

This configuration demonstrates:
- Imitating basic authorization
- JSON posts
- Automatic data type inference

```json
{
  "api": {
    "base_url": "https://api-demo.com"
  },
  "user_parameters": {
    "#token": "XXXXXX"
  },
  "request_parameters": {
    "method": "POST",
    "endpoint_path": "/v1/customers/events",
    "headers": {
      "Authorization": {
        "attr": "#token"
      },
      "Content-type": "application/csv"
    },
    "query_parameters": {}
  },
  "request_content": {
    "content_type": "JSON",
    "json_mapping": {
      "nesting_delimiter": "__",
      "chunk_size": 1,
      "column_data_types": {
        "autodetect": true,
        "datatype_override": []
      },
      "request_data_wrapper": "",
      "column_names_override": {}
    },
    "iterate_by_columns": []
  }
}
```


### Example with Iterations

```json
{
  "api": {
    "base_url": "https://api-demolcom"
  },
  "user_parameters": {},
  "request_parameters": {
    "method": "POST",
    "endpoint_path": "/v1/customers/{{user_id}}/events",
    "headers": {},
    "query_parameters": {}
  },
  "request_content": {
    "content_type": "JSON",
    "json_mapping": {
      "nesting_delimiter": "_",
      "chunk_size": 1,
      "column_data_types": {
        "autodetect": true,
        "datatype_override": []
      },
      "request_data_wrapper": "",
      "column_names_override": {}
    },
    "iterate_by_columns": [
      "user_id"
    ]
  }
}
```
