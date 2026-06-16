import { tool } from '@openrouter/agent';
import { z } from 'zod';

import fs from "fs/promises";

function showAction(setMessages, content, type) {
  setMessages(prev => prev.toSpliced(-1, 0, { role: "action", type, content }));
}

export default function getTools(messages, setMessages) {
  return [
    tool({
      name: 'read_file',
      description: 'Read from a file',
      inputSchema: z.string().describe('The file path'),
      outputSchema: z.object({
        success: z.boolean().describe('Was the read successful?'),
        content: z.string().describe('The file content')
      }),
      async execute(path) {
        try {
          const ret = { success: true, content: await fs.readFile(path) };
          showAction(setMessages, `Read ${path}`, "success");
          return ret;
        } catch (e) {
          showAction(setMessages, `Failed to read ${path}`, "error");
          return { success: false, content: "" };
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
          await fs.writeFile(param.path, param.content, "utf8");
          showAction(setMessages, `Wrote to ${param.path}`, "success");
          return true;
        } catch (e) {
          showAction(setMessages, `Failed to write to ${param.path}`, "error");
          return false;
        }
      },
    })
  ]
}