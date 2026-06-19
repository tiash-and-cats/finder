#!/usr/bin/env node
import React from 'react';
import App from "./app.js";
import login from "./login.js";
import fs from "fs/promises";
import chalk from "chalk";
import { render } from "ink";
import { OpenRouter, tool } from '@openrouter/agent';
import { Command } from 'commander';
import { marked } from 'marked';
import { markedTerminal } from 'marked-terminal';

import pkgjson from "./package.json" with { type: "json" };
import { defaultConfig } from "./config.js";
import { program, loginCmd, genconfigCmd } from "./cli.js";

program.version(pkgjson.version);
program.action(async function() {
  marked.use(markedTerminal({
    reflowText: true,
    width: process.stdout.columns || 80,
    
    heading: chalk.bold.magenta,
    code: chalk.bold.cyan,
    codespan: chalk.bold.cyan,
    tableOptions: { 
      colWidths: Array(4).fill(((process.stdout.columns || 80) - 8 /* table border + padding */) / 4), 
                 // assuming Find4U generates at most 4-col tables. hoping it does
      wordWrap: true,
      
      style: {
        head: ["cyan"]
      }
    }
  }));

  const token = await login();
  
  await render(
    <App openrouter={new OpenRouter({ apiKey: token })} marked={marked} />, 
    { 
      exitOnCtrlC: false,
      alternateScreen: true
    }
  ).waitUntilExit();
  
  process.exit(0);
});

loginCmd.action(async function(options) {
  await login(true, !!options.force);
});

genconfigCmd.action(async function() {
  await fs.writeFile("find4u.config.json", JSON.stringify(defaultConfig, null, 2), "utf-8");
  console.log("Successfully generated ./find4u.config.json");
});

program.parse();