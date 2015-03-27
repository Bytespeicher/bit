# bit

Bit is a simple URL shortener. It is not designed to scale very large.

Attention: This is highly alpha stuff and not yet ready for any kind of 
production use!

## CLI

The CLI tools are only available with newer Flask versions.

Available commands are:

* flask --app=bit initdb
    * Installs a new database
* flask --app=bit addkey --key KEY [--limit LIMIT]
    * Adds a new API key
    * KEY must be 32 characters long
    * LIMIT is the daily limit

## API
### short
#### URL

    /api/v1/short

#### Methods

    POST

#### Arguments

    key:  API key
          32 chars, hexadecimal

    url:  URL to shorten

    wish: will try to return this as link identifier, the API may return 
          another identifier than the one specified
          32 chars
          optional

#### Example

```json
{
    "key": "1234567890ABCDEF",
    "url": "http://www.example.com/example",
    "wish": "MyWish"
}
```

### long

#### URL

    /api/v1/long

#### Methods

    POST

#### Arguments

    key:  API key
          32 chars, hexadecimal

    id:   id of URL to expand

#### Example

```json
{
    "key": "1234567890ABCDEF",
    "id":  "4af3fjnnW",
}
```
