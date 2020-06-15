# KBC Generic Writer

Description

**Table of contents:**  
  
[TOC]


# Functionality notes

# Configuration

**Parameters**

- **path** – An URL of the page.
- **headers** - Array of HTTP headers to send. You may include User parameters as a value
```json
"headers": [
      {
        "key": "Authorization",
        "value": {
          "attr": "#token"
        }
      }
    ]
```

- **additional_requests_pars** - (OPT) additional kwarg parameters that are accepted by the 
Python [Requests library](https://2.python-requests.org/en/master/user/quickstart/#make-a-request), get method. 
**NOTE** the `'false','true'` string values are converted to boolean, objects will be treated as python dictionaries
```json
"additional_requests_pars": [
      {
        "key": "verify",
        "value": "false"
      },
      {
        "key": "params",
        "value": {
          "date": {
            "attr": "date"
          }
        }
      }
    ]
```
- **user_parameters** – A list of user parameters that is are accessible from within headers and additional parameters. This is useful for storing
for example user credentials that are to be filled in a login form. Appending `#` sign before the attribute name will hash the value and store it securely
within the configuration (recommended for passwords). The value may be scalar or a supported function. You can access user parameters vis:
```json
"value": {
          "attr": "#token"
        }
```


## Dynamic Functions

The application support functions that may be applied on parameters in the configuration to get dynamic values.

Currently these functions work only in the `user_parameters` scope. Place the required function object instead of the user parameter value.

**Function object**

```json
{ "function": "string_to_date",
                "args": [
                  "yesterday",
                  "%Y-%m-%d"
                ]
              }
```

**Function Nesting**

Nesting of functions is supported:

```json
{
   "user_parameters":{
      "url":{
         "function":"concat",
         "args":[
            "http://example.com",
            "/test?date=",
            { "function": "string_to_date",
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

### string_to_date

Function converting string value into a datestring in specified format. The value may be either date in `YYYY-MM-DD` format,
or a relative period e.g. `5 hours ago`, `yesterday`,`3 days ago`, `4 months ago`, `2 years ago`, `today`.

The result is returned as a date string in the specified format, by default `%Y-%m-%d`

The function takes two arguments:

1. [REQ] Date string
2. [OPT] result date format. The format should be defined as in http://strftime.org/



**Example**

```json
{
   "user_parameters":{
      "yesterday_date":{
         "function":"string_to_date",
         "args":[
            "yesterday",
            "%Y-%m-%d"
         ]
      }
   }
}
```

The above value is then available in step contexts as:

```json
"to_date": {"attr": "yesterday_date"}
```

### concat

Concat an array of strings.

The function takes an array of strings to concat as an argument



**Example**

```json
{
   "user_parameters":{
      "url":{
         "function":"concat",
         "args":[
            "http://example.com",
            "/test"
         ]
      }
   }
}
```

The above value is then available in step contexts as:

```json
"url": {"attr": "url"}
```



# Configruation example

```json
{
    "path": "https://example.com/test",
    "mode": "JSON",
    "method": "POST",
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
    "headers": [
      {
        "key": "Authorization",
        "value": {
          "attr": "#token"
        }
      },
      {
        "key": "Content-Type",
        "value": "application/json"
      }
    ],
    "additional_requests_pars": [
      {
        "key": "params",
        "value": {
          "date": {
            "attr": "date"
          }
        }
      }
    ],
    "json_data_config": {
      "chunk_size": 5,
      "delimiter": "_",
      "request_data_wrapper": "{ \"data\": {{data}}}",
      "column_types": [
        {
          "column": "bool_bool2",
          "type": "number"
        },
        {
          "column": "bool_bool1",
          "type": "bool"
        },
        {
          "column": "id",
          "type": "string"
        },
        {
          "column": "field.id",
          "type": "string"
        },
        {
          "column": "ansconcat",
          "type": "string"
        },
        {
          "column": "time_submitted",
          "type": "string"
        },
        {
          "column": "id2",
          "type": "string"
        },
        {
          "column": "time_11",
          "type": "bool"
        },
        {
          "column": "time_reviewed_r2",
          "type": "bool"
        },
        {
          "column": "time_reviewed_r1_r1",
          "type": "bool"
        }
      ]
    },
    "debug": true
  }
```



## Development

If required, change local data folder (the `CUSTOM_FOLDER` placeholder) path to your custom path in the docker-compose file:

```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone this repository, init the workspace and run the component with following command:

```
git clone repo_path my-new-component
cd my-new-component
docker-compose build
docker-compose run --rm dev
```

Run the test suite and lint check using this command:

```
docker-compose run --rm test
```

# Integration

For information about deployment and integration with KBC, please refer to the [deployment section of developers documentation](https://developers.keboola.com/extend/component/deployment/) 