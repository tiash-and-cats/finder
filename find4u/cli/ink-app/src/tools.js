import { tool } from '@openrouter/agent';
import { z } from 'zod';

import fs from "fs/promises";

function showAction(setMessages, content, type) {
  setMessages(prev => prev.toSpliced(-1, 0, { role: "action", type, content }));
}

function getFSTools(setMessages) {
  return [
    tool({
      name: 'read_file',
      description: 'Read from a file',
      inputSchema: z.string().describe('The file path'),
      outputSchema: z.object({
        success: z.boolean().describe('Was the read successful?'),
        content: z.string().describe('The file content, or, if unsuccessful, the error message')
      }),
      async execute(path) {
        try {
          const ret = { success: true, content: await fs.readFile(path, "utf8") };
          showAction(setMessages, `Read ${path}`, "success");
          return ret;
        } catch (e) {
          showAction(setMessages, `Failed to read ${path}`, "error");
          return { success: false, content: e.message };
        }
      },
    }),
    tool({
      name: 'write_file',
      description: 'Write to a file using utf-8',
      inputSchema: z.object({
        path: z.string().describe('The file path'),
        content: z.string().describe('The file content'),
      }),
      outputSchema: z.boolean().describe('Was the write successful?'),
      async execute(param) {
        try {
          if (param.path.endsWith("find4u.config.json")) {
            throw new Error("Find4U is prohibited from modifying find4u.config.json");
          }
          await fs.writeFile(param.path, param.content, "utf8");
          showAction(setMessages, `Wrote to ${param.path}`, "success");
          return true;
        } catch (e) {
          showAction(setMessages, `Failed to write to ${param.path}`, "error");
          return false;
        }
      },
    })
  ];
}

export default function getTools(confTools, setMessages) {
  const mapping = {
    "fstools": getFSTools
  };
  const tools = [];
  for (const tool of confTools) {
    if (!Object.hasOwn(mapping, tool)) {
      showAction(setMessages, `Tool ${tool} does not exist, skipping`, "warning");
      continue;
    }
    tools.push(...mapping[tool](setMessages));
  }
  return tools;
}