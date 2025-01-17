# Keboola Generic Writer

Description

**Table of Contents:**

[TOC]

The Keboola Generic writer component allows you to write data to a specified endpoint in a specified format. It currently supports a single
table and a single endpoint per configuration.

The data can be sent in two ways:

1. **Send all content at once:** Data is sent either as BINARY or JSON in chunks.
2. **[Iterate](/extend/generic-writer/configuration/#iterate-by-columns) through each row:** Data is sent iteratively, as specified in the input data. By default, 1 row = 1 iteration. This mode allows dynamic changes to the endpoint
   based on input using placeholders (e.g., `www.example.com/api/user/{{id}}`). It can also send data with different user parameters present in the input table.

### Configuration Parameters

*Click on the section names for more details.*

- [**api**](/extend/generic-writer/configuration/#api/) --- [REQUIRED] Specifies the basic properties of the API.
    - [**base_url**](/extend/generic-writer/configuration/#base-url) ---  [REQUIRED] Defines the URL to which the API
      requests are sent.
    - [**authentication**](/extend/generic-writer/configuration/#authentication) --- Configuration for APIs that are not public.
    - [**retry_config**](/extend/generic-writer/configuration/#retry-config) --- Automatically retries failed HTTP requests.
    - [**default_query_parameters**](/extend/generic-writer/configuration/#default-query-parameters) --- Default query parameters sent with each API call.
    - [**default_headers**](/extend/generic-writer/configuration/#default-headers) --- Default query headers sent with each API call.
    - [**ssl_verification**](/extend/generic-writer/configuration/#ssl-verification) --- Option to disable SSL certificate verification (use with caution).
    - [**timeout**](/extend/generic-writer/configuration/#timeout) --- Maximum time (in seconds) the component waits after each request (defaults to None if not set).
- [**user_parameters**](/extend/generic-writer/configuration/#user-parameters) --- User-defined parameters used in various contexts, such as passwords. Supports dynamic functions.
- [**request_parameters**](/extend/generic-writer/configuration/#request-parameters) -- [REQUIRED] HTTP parameters of the request:
    - [**method**](/extend/generic-writer/configuration/#method) --- [REQUIRED] Specifies the HTTP method of the requests.
    - [**endpoint_path**](/extend/generic-writer/configuration/#enpoint-path) --- [REQUIRED] Defines the relative path of the endpoint.
    - [**query_parameters**](/extend/generic-writer/configuration/#query-parameters) --- Query parameters sent with each request.
    - [**headers**](/extend/generic-writer/configuration/#headers) --- Headers sent with each request.
- [**request_content**](/extend/generic-writer/configuration/#request-content) --- [REQUIRED] Defines how the data is sent:
    - [**content_type**](/extend/generic-writer/configuration/#content-type) --- [REQUIRED] Specifies the data transfer format (e.g., JSON, binary file, empty, etc.)
    - [**json_mapping**](/extend/generic-writer/configuration/#json-mapping) --- Defines the CSV2-to-JSON conversion for JSON content type.
    - [**iterate_by_columns**](/extend/generic-writer/configuration/#iterate-by-columns) --- Specifies a set of columns in the input data excluded from the content. These columns may be used as placeholders
      in request_options. The input table is iterated row by row (1 row = 1 request).

Additionally, there are pre-defined [**dynamic functions**](/extend/generic-writer/configuration/#dynamic-functions) available,
providing extra flexibility when needed.

### Configuration Map

The following sample configuration shows various configuration options and their nesting. Use the map to
navigate between them.

```json
{
  "parameters": {
    "debug": false,
    "api": {
      "base_url": "https://example.com/api",
      "default_query_parameters": {
        "content_type": "json"
      },
      "default_headers": {
        "Authorization": {
          "attr": "#token"
        }
      },
      "retry_config": {
        "max_retries": 5,
        "codes": [
          500,
          429
        ]
      },
      "ssl_verification": true,
      "timeout": 5
    },
    "user_parameters": {
      "#token": "Bearer 123456",
      "date": {
        "function": "concat",
        "args": [
          {
            "function": "string_to_date",
            "args": [
              "yesterday",
              "%Y-%m-%d"
            ]
          },
          "T"
        ]
      }
    },
    "request_parameters": {
      "method": "POST",
      "endpoint_path": "/customer/[[id]]",
      "headers": {
        "Content-Type": "application/json"
      },
      "query_parameters": {
        "date": {
          "attr": "date"
        }
      }
    },
    "request_content": {
      "content_type": "JSON",
      "json_mapping": {
        "nesting_delimiter": "__",
        "chunk_size": 100,
        "column_data_types": {
          "autodetect": true,
          "datatype_override": [
            {
              "column": "phone",
              "type": "string"
            },
            {
              "column": "rank",
              "type": "number"
            },
            {
              "column": "is_active",
              "type": "bool"
            }
          ]
        },
        "request_data_wrapper": "{ \"data\": [[data]]}",
        "column_names_override": {
          "full_name": "FULL|NAME"
        }
      },
      "iterate_by_columns": [
        "id"
      ]
    }
  }
}
```

## API

Defines the basic properties of the API that may be shared for multiple endpoints, such as authentication, base URL,
etc.

### Base URL

The URL of the endpoint where the payload is being sent, e.g., `www.example.com/api/v1`.

**Note:** The URL may contain placeholders for iterations wrapped in `[[]]`,e.g., ``www.example.com/api/v[[api_version]]``.  
However, in most cases, this should be set at the `endpoint_path` level.

The parameter `api_version` must be specified in the `user_parameters` section or in the source data itself if the column is
set as an iteration parameter column.

### Retry Config

Configure parameters for retrying requests in case of failure.

- `max_retries` --- Maximum number of retries before failing (default `1`).
- `codes` --- List of HTTP codes to retry on, e.g., [503, 429] (default `(500, 502, 504)`).
- `backoff_factor` --- Exponential backoff factor (default `0.3`).

```json
"api": {
"base_url": "https://example.com/api",
"retry_config": {
"max_retries": 5,
"backoff_factor": 0.3
"codes": [
500,
429
]
}
}
```

### Default Query Parameters

Define parameters to be sent with each request. This is useful for authentication or when creating templates for the Generic Writer.

**Note:** You can reference parameters defined in `user_parameters` using the syntax `{"attr":"SOME_KEY"}`.

```json
        "api": {
"base_url": "https://example.com/api",
"default_query_parameters": {
"content
_type":"json",
"token": {
"attr": "#token"
}
}
```

### Default Headers

Define default headers sent with each request.

**Note:** Parameters in `user_parameters` can also be referenced using the syntax `{"attr":"SOME_KEY"}`.

```json
        "api": {
"base_url": "https://example.com/api",
"default_headers": {
"Authorization": {"attr": "#token"}
}
```

### Authentication

Some APIs require authenticated requests. This section allows you to select from predefined authentication methods.

The authentication object is always in the following format:

```json

{
  "type": "{SUPPORTED_TYPE}",
  "parameters": {
    "some_parameter": "test_user"
  }
}
```

**Note:** Parameters may be referenced from the `user_parameters` section using the syntax `{"attr":""}`.

See [example 025](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/025-simple-json-basic-http-auth-from-user-params).

#### Basic HTTP authentication

Use a username and password for authentication.

**Example**:

```json
"api": {
"base_url": "http://localhost:8000",
"authentication": {
"type": "BasicHttp",
"parameters": {
"username": "test_user",
"#password": "pass"
}
}
}
```

See [example 024](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/024-simple-json-basic-http-auth).

#### Bearer Token

Use a `Bearer token` in the header (e.g., `"authorization": "Bearer XXXX""`).

**Example**:

```json
{
  "api": {
    "base_url": "http://localhost:8000",
    "authentication": {
      "type": "BearerToken",
      "parameters": {
        "#token": "XXXX"
      }
    }
  }
}
```

See [example 030](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/030-bearer-token-auth).

#### API key in a query

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "ApiKey",
      "parameters": {
        "#token": {
          "attr": "#__password"
        },
        "key": "token",
        "position": "query"
      }
    }
  },
  "user_parameters": {
    "#__password": "XXXX"
  }
}
```

See [example 031](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/031-auth-token-query)

#### API key in a header

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "ApiKey",
      "parameters": {
        "#token": {
          "attr": "#__password"
        },
        "key": "token",
        "position": "headers"
      }
    }
  },
  "user_parameters": {
    "#__password": "XXXX"
  }
}
```

See [example 032](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/032-auth-token-header)

#### Login — token in a query

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "Login",
      "parameters": {
        "loginRequest": {
          "endpoint": "/033-auth-login-query/login",
          "method": "GET",
          "headers": {
            "X-Login": "JohnDoe",
            "X-Password": {
              "attr": "#__password"
            }
          }
        },
        "apiRequest": {
          "query": {
            "token": {
              "response": "authorization.token"
            }
          }
        }
      }
    }
  },
  "user_parameters": {
    "#__password": "TopSecret"
  }
}
```

See [example 033](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/033-auth-login-query).

#### Login — token in a header

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "Login",
      "parameters": {
        "loginRequest": {
          "endpoint": "/034-auth-login/login",
          "method": "GET",
          "headers": {
            "X-Login": "JohnDoe",
            "X-Password": {
              "attr": "#__password"
            }
          }
        },
        "apiRequest": {
          "headers": {
            "X-ApiToken": {
              "response": "authorization.token"
            }
          }
        }
      }
    }
  },
  "user_parameters": {
    "#__password": "TopSecret"
  }
}
```

See [example 034](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/034-auth-login).

#### OAuth 2.0 client credentials — GET

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "OAuth20ClientCredentials",
      "format": "json",
      "parameters": {
        "loginRequest": {
          "endpoint": "/035-oauth_basic/login",
          "method": "GET",
          "type": "client_secret_basic",
          "headers": {}
        },
        "apiRequest": {
          "headers": {
            "X-ApiToken": {
              "response": "access_token"
            }
          }
        }
      }
    }
  },
  "user_parameters": {
    "#__password": "TopSecret"
  }
}
```

See [example 035](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/035-oauth_basic).

#### OAuth 2.0 client credentials — POST JSON

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "OAuth20ClientCredentials",
      "format": "json",
      "parameters": {
        "loginRequest": {
          "endpoint": "/036-oauth_post_json/login",
          "method": "POST",
          "type": "client_secret_post_json",
          "headers": {}
        },
        "apiRequest": {
          "headers": {
            "X-ApiToken": {
              "response": "access_token"
            }
          }
        }
      }
    }
  },
  "user_parameters": {
    "#__password": "TopSecret"
  }
}
```

See [example 036](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/036-oauth_post_json).

#### OAuth 2.0 client credentials — POST form

**Example**:

```json
{
  "api": {
    "base_url": "http://mock-server:80",
    "authentication": {
      "type": "OAuth20ClientCredentials",
      "format": "json",
      "parameters": {
        "loginRequest": {
          "endpoint": "/037-oauth_post_form/login",
          "method": "GET",
          "type": "client_secret_post_form",
          "headers": {}
        },
        "apiRequest": {
          "headers": {
            "X-ApiToken": {
              "response": "access_token"
            }
          }
        }
      }
    }
  },
  "user_parameters": {
    "#__password": "TopSecret"
  }
}
```

See [example 037](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/037-oauth_post_form).

### SSL Verification

Allows turning off SSL certificate verification. **Use with caution.** When set to `false`, SSL verification is disabled.

```json

{
  "api": {
    "base_url": "http://localhost:8000",
    "ssl_verification": false
  }
}
```

### Timeout

Defines the maximum timeout for each request. If not set, the default value (`None`) is used:

Possible values: int, float

For more information, refer to the [requests documentation](https://requests.readthedocs.io/en/stable/user/advanced/#timeouts).

## User Parameters

User parameters can be defined for use in various contexts, such as passwords. This section also supports [dynamic functions](https://developers.keboola.com/extend/generic-writer/configuration/#dynamic-functions).

It allows referencing other values from `user_parameters` referenced by the notation `{"attr":"par"}`.

**Note:** Parameters prefixed with `#` are encrypted in the Keboola platform upon saving the configuration.

```json
        "user_parameters": {
"#token": "Bearer 123456",
"date": {
"function": "concat",
"args": [
{
"function": "string_to_date",
"args": [
"yesterday",
"%Y-%m-%d"
]
},
"T"
]
}
}
```

### Referencing Parameters

Parameters defined in this section can be referenced using the `{"attr":"PARAMETER_KEY"}` syntax in:

- `user_parameters` section itself.
- [`api.default_query_parameters`](/extend/generic-writer/configuration/#default-query-parameters)
- [`api.default_headers`](/extend/generic-writer/configuration/#default-headers)
- [`request_parameters.headers`](/extend/generic-writer/configuration/#headers)
- [`request_parameters.query parameters`](/extend/generic-writer/configuration/#query-parameters)

See example [010](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/010-simple-json-user-parameters-various) for more details.

## Request Parameters

Define parameters for HTTP requests.

### Method

Request method: POST, PUT, UPDATE, DELETE, etc.

Supported methods: `['GET', 'POST', 'PATCH', 'UPDATE', 'PUT', 'DELETE']`

```json
"request_parameters": {
"method": "POST",
...
```

### Endpoint Path

The relative path of the endpoint. The final request URL combines `base_url` and `endpoint_path`.

**Example:**
If `base_url` is `https://example.com/api` and `endpoint_path` is `/customer`, the resulting URL
is: `https://example.com/api/customer`.

**Note:** The `enpoint_path` can be dynamically changed using [iteration columns](/extend/generic-writer/configuration/#iterate-by-columns); e.g., `/orders/[[id]]` as seen
in [example 005](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/005-json-iterations/).

```json

"request_parameters": {
"method": "POST",
"endpoint_path": "/customer",
...
```

### Headers

Define default headers sent with each request.

**Note:** You can reference `user_parameters` using the `{"attr":"SOME_KEY"}` syntax.

```json
"request_parameters": {
"method": "POST",
"endpoint_path": "/customer",
"headers": {
"Last-updated": 123343534
},
...
```

See [example 006](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/006-simple-json-custom-headers/).

### Query Parameters

Define default query parameters sent with each request.

**Note:** Parameters can reference `user_parameters` with the `{"attr":"SOME_KEY"}` syntax.

```json
"request_parameters": {
"method": "POST",
"endpoint_path": "/customer/[[id]]",
"query_parameters": {
"dryRun": true,
"date": {
"attr": "date"
}
}
}
```

See [example 009](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/009-simple-json-request-parameters/).

## Request Content

Defines how to process the input data and how the sent content should look.

### Content Type

Specifies how the input table is translated into a request:

- `JSON`: The input table is converted into JSON (see `json_mapping`) and sent as `application/json`.
  See [example 001](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/001-simple-json/).
- `JSON_URL_ENCODED`: The input table is converted into JSON and sent as `application/x-www-form-urlencoded`.
  See [example 021](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/021-simple-json-url-encoded-form/).
- `BINARY`: The input table is sent as binary data, similar to `curl --data-binary`.
  See [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_simple/).
- `BINARY-GZ`: The input is sent as gzipped binary data.
  See [example](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/tests/functional/binary_gz/).
- `EMPTY_REQUEST`: Sends empty requests. Useful for triggerring webhooks, DELETE calls, etc. As many requests as
  there are rows in the input are sent. Useful with `iterate_by_columns` enabled to trigger multiple endpoints.
  See [example 022](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/022-empty-request-iterations-delete/).

```json

"request_content": {
"content_type": "JSON",
....
```

### JSON Mapping

[REQUIRED for JSON based content type] 
This section defines the CSV-to-JSON conversion.

#### Nesting delimiter

Defines the string used for nesting JSON objects. You can define nested objects based on column names.

For example, if set to `__`, a column named `address__streed` will be converted to `{"address"{"street":"COLUMN_VALUE"}}`.

```json
"request_content": {
"content_type": "JSON",
"json_mapping": {
"nesting_delimiter": "_",
...
```

See
example [008](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/008-simple-json-nested-object-delimiter/).

#### Chunk size

Defines the number of rows sent in a single request. 
- `1`: Sends each row as a single object, e.g., `{}` (
see [example 002](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/002-simple-json-chunked-single/)).
- `>1`: Sends rows as an array of objects, e.g., `[{}, {}]` (
see [example 003](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/003-simple-json-chunked-multi/)).

```json
"request_content": {
"content_type": "JSON",
"json_mapping": {
"nesting_delimiter": "_",
"chunk_size": 1,
...
```

#### Column datatypes

Optional configuration for column types. This version supports three levels of nesting and three datatypes:

- `bool`: Boolean values. Case-insensitive conversions: 
    - `t`, `true`, `yes`, `1`,`"1"` -> `True` 
    - `f`, `false`, `no` -> `False`
- `string`: String values.
- `number`: Numeric values.
- `object`: Valid JSON arrays or JSON objects (e.g., ["1","2"], {"key":"val"}).

##### Autodetect

Set to `true` by default. Automatically detects column types unless overriden by `datatype_override`.

##### Column datatype override

[OPTIONAL]

In most cases, the `autodetect` option handles datatype conversion correctly. However, there are scenarios where
you may need to force the datatype conversion. For example, to ensure that the `phone_number` column is treated as a string, you can specify
`"phone_number":"string"`.

**Available datatype options:*

- `string`: Always interpret the value as a string.
- `number`: Interpret the value as numeric.
- `bool`: Interpret the value as a Boolean.
  - Case-insensitive conversions: 
    - `t`, `true`, `yes` -> `True` 
    - `f`, `false`, `no` -> `False`
- `object`: Interpret the value as a valid JSON array or object (e.g., ["1","2"], {"key":"val"}).

**Note:** If the `autodetect` option is turned off, all unspecified columns will default to `string`.

```json
"request_content": {
"content_type": "JSON",
"json_mapping": {
"nesting_delimiter": "_",
"chunk_size": 1,
"column_data_types": {
"autodetect": true,
"datatype_override": [
{
"column": "phone",
"type": "string"
}, {
"column": "rank",
"type": "number"
}, {
"column": "is_active",
"type": "bool"
}
]
}
}
}
```

See [example 007](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/007-simple-json-force-datatype/).

#### Request Data Wrapper

[OPTIONAL]

A wrapper or mask can be applied to the parsed data, encoded as JSON. For example:

```json
"request_content": {
"content_type": "JSON",
"json_mapping": {
"nesting_delimiter": "__",
"chunk_size": 1,
"request_data_wrapper": "{ \"data\": [[data]]}",
...
```

Given a single column `user__id` and `chunksize` = 2, the above will send requests like this:

```json
{
  "data": [
    {
      "user": {
        "id": 1
      }
    },
    {
      "user": {
        "id": 2
      }
    }
  ]
}
```

See
example [012](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/012-simple-json-request-data-wrapper/).

#### Column names override

You can override specific column names using the `column_names_override` parameter, allowing you to generate fields with
characters not supported in Storage column names.

**Notes:** 
- This is applied **after** column type definitions, so refer to the original name in the `column_types`
configuration.
- Nested objects renaming is supported. The rename applies to the leaf node.

Example: 
Given the configuration `"address___city":"city.address"`, with a delimiter set to `___`, the result would be: `{"address":{"city.address":"SOME_VALUE"}}`.

See [example 23](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/023-simple-json-nested-object-rename-column/).

**Example:**

```json
"request_content": {
"content_type": "JSON",
"json_mapping": {
"nesting_delimiter": "_",
"chunk_size": 1,
"column_names_override": {
"field_id": "field-id",
"full_name": "FULL.NAME"
}
...
```

For more examples, see:
[example 20](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/020-simple-json-column-name-override/)
and [example 23](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/023-simple-json-nested-object-rename-column/).

### Iterate By Columns

This parameter allows requests to be performed iteratively based on data from specific columns in the source table. These column values can be used as
placeholders within `request_options`. The input table is processed row by row (1 row = 1 request).

```json
"request_content": {
"content_type": "JSON",
"iterate_by_columns": [
"id", "date"
]
}

```

These values will be injected into:

- `request_parameters.endpoint_path` (if a placeholder like `/user/[[id]]` is used).
- `user_parameters` (replacing parameters with matching names). This
  allows for dynamically changing request parameters, such as `www.example.com/api/user?date=xx`, where the `date`
  value is specified as follows:

```json

"request_parameters": {
"method": "POST",
"endpoint_path": "/customer/[[id]]",
"query_parameters": {
"date": {
"attr": "date"
}
}
}



```

**Note:** When `iterate_by_columns` is enabled, the `chunk_size` in JSON mapping is overridden to `1`.

**Example configurations:**

- [Example 005](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/005-json-iterations/)
- Empty request with iterations [example 004](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/004-empty-request-iterations/),
  [example 22](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/022-empty-request-iterations-delete/)
- [Example 011: placeholders in query parameters](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/docs/examples/011-simple-json-user-parameters-from-iterations/)

##### Example Input Table

| id | date       | name  | email      | address |
|----|------------|-------|------------|---------|
| 1  | 01.01.2020 | David | d@test.com | asd     |
| 2  | 01.02.2020 | Tom   | t@test.com | asd     |

Consider the following request options:

```json
"request_parameters": {
"method": "POST",
"endpoint_path": "/user/[[id]]",
"query_parameters": {
"date": {
"attr": "date"
}
}
},
"request_content": {
"content_type": "JSON",
"iterate_by_columns": [
"id", "date"
]
}
}

```

The writer will run in two iterations:

**First request:**

| name  | email      | address |
|-------|------------|---------|
| David | d@test.com | asd     |

Sent to `www.example.com/api/user/1?date=01.01.2020`.

**Second request:** 

| name  | email      | address |
|-------|------------|---------|
| Tom   | t@test.com | asd     |

Sent to `www.example.com/api/user/2?date=01.02.2020`.

## Dynamic Functions

This application supports dynamic functions that can be applied to parameters in the configuration for generating values dynamically.

Currently, functions only work within the `user_parameters` scope. Place the required function object instead of the
user parameter value.

Function values can refer to other user parameters using the syntax: `{"attr": "custom_par"}`.

**Note:** If you require additional functions, let us know or submit a pull request to
our [repository](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/). It's as simple as adding an
arbitrary method to the [UserFunctions class](https://bitbucket.org/kds_consulting_team/kds-team.wr-generic/src/master/src/user_functions.py#lines-7).

**Function object**

```json
{
  "function": "string_to_date",
  "args": [
    "yesterday",
    "%Y-%m-%d"
  ]
}
```

#### Function Nesting

Nesting of functions is supported:

```json
{
  "user_parameters": {
    "url": {
      "function": "concat",
      "args": [
        "http://example.com",
        "/test?date=",
        {
          "function": "string_to_date",
          "args": [
            "yesterday",
            "%Y-%m-%d"
          ]
        }
      ]
    }
  }
}

```

#### string_to_date

This function converts a string into a formatted date string. The input can be:
- A specific date in the `YYYY-MM-DD` format (e.g., `2024-01-01`). 
- A relative period (e.g., `5 hours ago`, `yesterday`,`3 days ago`, `4 months ago`, `2 years ago`, `today`).

The result is returned as a date string in the specified format (default: `%Y-%m-%d`).

The function takes two arguments:

1. [REQUIRED] Date string
2. [OPTIONAL] Desired date format (defined as in http://strftime.org/)

**Example:**

```json
{
  "user_parameters": {
    "yesterday_date": {
      "function": "string_to_date",
      "args": [
        "yesterday",
        "%Y-%m-%d"
      ]
    }
  }
}
```

The above value is then available in [supported contexts](/extend/generic-writer/configuration/#referencing-parameters)
as follows:

```json
"to_date": {"attr": "yesterday_date"}
```

#### concat

Concatenates an array of strings into a single value.

The function accepts an array of strings as its argument and concatenates them into one.

**Example:**

```json
{
  "user_parameters": {
    "url": {
      "function": "concat",
      "args": [
        "http://example.com",
        "/test"
      ]
    }
  }
}
```

The resulting value is then available in supported contexts as follows:

```json
"url": {"attr": "url"}
```

#### base64_encode

Encodes a string in BASE64 format.

**Example:**

```json
{
  "user_parameters": {
    "token": {
      "function": "base64_encode",
      "args": [
        "user:pass"
      ]
    }
  }
}
```

The resulting value is then available in contexts as follows:

```json
"token": {"attr": "token"}
```

## Development

To customize the local data folder path, replace the `CUSTOM_FOLDER` placeholder with your desired path in the docker-compose.yml file:

```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone this repository, initialize the workspace, and run the component using the following commands:

```
git clone repo_path my-new-component
cd my-new-component
docker-compose build
docker-compose run --rm dev
```

Run the test suite and perform lint checks using this command:

```
docker-compose run --rm test
```

# Integration

For details about deployment and integration with Keboola, refer to
the [deployment section of the developer documentation](https://developers.keboola.com/extend/component/deployment/). 