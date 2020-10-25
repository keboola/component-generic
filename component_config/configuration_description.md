Writes data to a specified endpoint in a specified format. Supports single table and single endpoint per configuration.

Works in two modes:

1. Basic mode - where the input data is sent to the endpoint in a specified format
2. Iteration mode - where the data is sent in iterations specified in the input data. By default 1 row = 1 iteration. 
This allows to change the endpoint dynamically based on the input using placeholders: `www.example.com/api/user/{{id}}`.
Or sending data with different user parameters that are present in the input table.

## Mode

Mode in what the data is transferred:

- `JSON` - input table is converted into a JSON (see json_data_config)
- `BINARY` - input table is sent as binary data (just like `curl --data-binary`)
- `BINRAY`-GZ - input is sent as gzipped binary data
- `EMPTY_REQUEST` - sends just empty requests. Usefull for triggerring webhooks, DELETE calls, etc. 
As many requests as there are rows on the input are sent. Useful with `iteration_mode` enabled to trigger multiple endpoints.

**NOTE** that you need to also setup the proper request headers manually.



### Example configuration

- imitating basic authorization, JSON posts, auto data type inference

```json
{
  "path": "https://api-demo.com/v1/customers/events",
  "mode": "JSON",
  "method": "POST",
  "user_parameters": {
    "#token": "XXXXXX",
    "token_encoded": {
      "function": "concat",
      "args": [
        "Basic ",
        {
          "function": "base64_encode",
          "args": [
            {
              "attr": "#token"
            }
          ]
        }
      ]
    }
  },
  "headers": [
    {
      "key": "Authorization",
      "value": {
        "attr": "token_encoded"
      }
    },
    {
      "key": "Content-type",
      "value": "application/csv"
    }
  ],
  "additional_requests_pars": [],
  "json_data_config": {
    "chunk_size": 1,
    "infer_types_for_unknown": true,
    "delimiter": "__",
    "column_types": []
  },
  "debug": true
}
```


** Example with Iterations:**

```json
{
  "path": "https://api-demolcom/v1/customers/{{user_id}}/events",
  "mode": "JSON",
  "method": "POST",
  "user_parameters": {
    "#token": "XXX",
    "token_encoded": {
      "function": "concat",
      "args": [
        "Basic ",
        {
          "function": "base64_encode",
          "args": [
            {
              "attr": "#token"
            }
          ]
        }
      ]
    }
  },
  "iteration_mode": {
    "iteration_par_columns": [
      "user_id"
    ]
  },
  "headers": [
    {
      "key": "Authorization",
      "value": {
        "attr": "token_encoded"
      }
    },
    {
      "key": "Content-type",
      "value": "application/csv"
    }
  ],
  "additional_requests_pars": [],
  "json_data_config": {
    "chunk_size": 1,
    "infer_types_for_unknown": true,
    "delimiter": "_",
    "column_types": []
  },
  "debug": true
}
```