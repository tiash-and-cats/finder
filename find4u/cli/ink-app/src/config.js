import getTools from "./tools.js";
import { tool } from '@openrouter/agent';
import { z } from 'zod';

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'; 

import fs from "fs/promises";
import path from "path";
import { existsSync } from 'fs';
import { configSchema } from './config-schema.js'

import pkgjson from "./package.json" with { type: "json" };

async function findUp(filename, startDir = process.cwd()) {
  let dir = path.resolve(startDir);

  while (true) {
    const candidate = path.join(dir, filename);
    try {
      await fs.access(candidate);
      return candidate; // found it
    } catch {
      // not found, move up
    }

    const parent = path.dirname(dir);
    if (parent === dir) {
      // reached root
      return null;
    }
    dir = parent;
  }
}

function showInitAction(setMessages, content, type) {
  setMessages(prev => [...prev, { role: "action", type, content }]);
}

function showAgentAction(setMessages, content, type) {
  setMessages(prev => prev.toSpliced(-1, 0, { role: "action", type, content }));
}

export const defaultConfig = {
  tools: {
    builtins: ["fstools"],
    mcp: []
  }
};

async function getConfig(setMessages) {
  const file = await findUp("find4u.config.json");
  if (file) {
    try {
      const configJson = JSON.parse(await fs.readFile(file, "utf-8"));
      return { file, config: configJson };
    } catch (e) {
      showInitAction(setMessages, `Invalid JSON in ${file} (${e}), using defaults`, "error");
      return { file, config: defaultConfig };
    }
  } else {
    showInitAction(setMessages, "Didn't find a config, using defaults", "info");
    return { file, config: defaultConfig };
  }
}

async function parseConfig(setMessages, config) {
  let result;
  if (!(result = configSchema.safeParse(config)).success) {
    showInitAction(setMessages, `Invalid config ${result.error.format()}, using default`, "error");
    return await parseConfig(setMessages, defaultConfig);
  }
  
  const ret = {};
  
  ret.tools = getTools(config.tools.builtins, setMessages);
  ret.exit = async() => {};
  
  if (config.tools.mcp.length) {
    const mcpClients = [];
    ret.exit = async() => {
      for (const mcpClient of mcpClients) {
        await mcpClient.close();
      }
    };
    
    for (const ctrans of config.tools.mcp) {
      let transport;
      const mcpClient = new Client({ name: `client-${mcpClients.length}`, version: pkgjson.version });
      switch (ctrans.type) {
        case "stdio": {
          transport = new StdioClientTransport({
            command: ctrans.cmd,
            args: ctrans.args,
            stderr: "ignore"
          });
          break;
        }
        case "streamable-http": {
          transport = new StreamableHTTPClientTransport(new URL(ctrans.url));
          break;
        }
      }
      await mcpClient.connect(transport);
      
      const { tools: mcpTools } = await mcpClient.listTools();
      ret.tools.push(...mcpTools.map(mcpTool => tool({
        name: mcpTool.name,
        description: mcpTool.description || `Execute ${mcpTool.name} remotely via MCP`,
        inputSchema: z.fromJSONSchema(mcpTool.inputSchema?.properties),
        execute: async (args) => {
          try {
            // Dispatches tool execution request safely over the stream tunnel
            const res = await mcpClient.callTool({
              name: mcpTool.name,
              arguments: args
            });
            showAgentAction(setMessages, `Called MCP tool ${mcpTool.name}`, "success");
            return res;
          } catch (err) {
            showAgentAction(setMessages, `Failed to call MCP tool ${mcpTool.name}`, "error");
            return { error: `MCP tool execution failure: ${err.message}` };
          }
        }
      })));
      
      mcpClients.push(mcpClient);
    }
  }
  
  return ret;
}

export default async function loadConfig(setMessages) {
  const conf = await getConfig(setMessages);
  const ret = await parseConfig(setMessages, conf.config);
  if (conf.file) showInitAction(setMessages, `Used config ${conf.file}`, "success");
  return ret;
}