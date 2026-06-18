# Properties

The Find4U CLI searches for a configuration file called `find4u.config.json` which describes what tools to expose to the agent. This file is documented here.

### Type: `object`

> ⚠️ Additional properties are not allowed.

| Property | Type | Required | Possible values | Description |
| -------- | ---- | -------- | --------------- | ----------- |
| tools | `object` | ✅ | object | Defines what tools to expose to the agent. |
| tools.builtins | `array` | ✅ | string | An array of built-in tools. The only one currently supported is 'fstools', which provides slightly-broken access to the filesystem. |
| tools.mcp | `array` | ✅ | [Stdio transport](#stdio-transport) or [Streamable HTTP transport](#streamable-http-transport) | An array of MCP servers. |


---

# Definitions

## Stdio transport

A [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#stdio).

#### Type: `object`

> ⚠️ Additional properties are not allowed.

| Property | Type | Required | Possible values | Description |
| -------- | ---- | -------- | --------------- | ----------- |
| type | `const` | ✅ | `stdio` |  |
| cmd | `string` | ✅ | string | The command to run. |
| args | `array` | ✅ | string | An array of arguments. |

## Streamable HTTP transport

A [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#streamable-http).

#### Type: `object`

> ⚠️ Additional properties are not allowed.

| Property | Type | Required | Possible values | Description |
| -------- | ---- | -------- | --------------- | ----------- |
| type | `const` | ✅ | `streamable-http` |  |
| url | `string` | ✅ | Format: [`uri`](https://json-schema.org/understanding-json-schema/reference/string#built-in-formats) | The URL to the MCP server. |


---

Markdown generated with [jsonschema-markdown](https://github.com/elisiariocouto/jsonschema-markdown).
