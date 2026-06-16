#!/usr/bin/env node
import React from 'react';
import App from "./app.js";
import login from "./login.js";
import { render } from "ink";
import { OpenRouter, tool } from '@openrouter/agent';

import { marked } from 'marked';
import { markedTerminal } from 'marked-terminal';
marked.use(markedTerminal());

const token = await login();

process.stdout.write("\x1b[?1049h");

await render(
  <App openrouter={new OpenRouter({ apiKey: token })} marked={marked} />, 
  { exitOnCtrlC: false }
).waitUntilExit();

process.stdout.write("\x1b[?1049l");
process.exit(0);