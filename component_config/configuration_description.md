The data can be sent in two ways:

1. Send all content at once - either BINARY or JSON in chunks
2. [Iterate](/extend/generic-writer/configuration/#iterate-by-columns) through each row - where the data is sent in
   iterations specified in the input data. By default 1 row = 1 iteration. This allows to change the endpoint
   dynamically based on the input using placeholders: `www.example.com/api/user/{{id}}`. Or sending data with different
   user parameters that are present in the input table.

Data can be sent in different content types:
- `JSON` - input table is converted into a JSON (see `json_mapping`) sent as `application/json` type.
  See [example 001](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/001-simple-json/)
- `JSON_URL_ENCODED` - input table is converted into a JSON and sent as `application/x-www-form-urlencoded`.
  See [example 021](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/021-simple-json-url-encoded-form/)
- `BINARY` - input table is sent as binary data (just like `curl --data-binary`).
  See [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_simple/)
- `BINARY-GZ` - input is sent as gzipped binary data.
  See [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_gz/)
- `EMPTY_REQUEST` - sends just empty requests. Usefull for triggerring webhooks, DELETE calls, etc. As many requests as
  there are rows on the input are sent. Useful with `iterate_by_columns` enabled to trigger multiple endpoints.
  See [example 022](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/022-empty-request-iterations-delete/)

### Example configuration

- imitating basic authorization, JSON posts, auto data type inference

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


** Example with Iterations:**

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