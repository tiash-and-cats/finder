import { z } from 'zod';

export const configSchema = z.object({ 
  tools: z.object({
    builtins: z.array(z.string()).describe("An array of built-in tools. The " +
                                           "only one currently supported is 'fstools'," +
                                           " which provides slightly-broken access" +
                                           " to the filesystem."),
    mcp: z.array(z.discriminatedUnion("type", [
      z.object({
        type: z.literal("stdio"),
        cmd: z.string().describe("The command to run."),
        args: z.array(z.string()).describe("An array of arguments.")
      }).meta({ title: "Stdio transport" }).describe("A [stdio transport]" +
                  "(https://modelcontextprotocol.io/specification/" + 
                  "2025-11-25/basic/transports#stdio)."),
      z.object({
        type: z.literal("streamable-http"),
        url: z.url().describe("The URL to the MCP server.")
      }).meta({ title: "Streamable HTTP transport" }).describe("A [Streamable HTTP transport]" +
                  "(https://modelcontextprotocol.io/specification/" + 
                  "2025-11-25/basic/transports#streamable-http).")
    ])).describe("An array of MCP servers.")
  }).describe("Defines what tools to expose to the agent.")
}).describe("The Find4U CLI searches for a configuration file called `find4u.config.json` which describes what tools to expose to the agent. This file is documented here.");