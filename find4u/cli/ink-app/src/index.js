#!/usr/bin/env node
import React from 'react';
import App from "./app.js";
import login from "./login.js";
import fs from "fs/promises";
import chalk from "chalk";
import { render } from "ink";
import { OpenRouter, tool } from '@openrouter/agent';
import { Command } from 'commander';

import pkgjson from "./package.json" with { type: "json" };
import { defaultConfig } from "./config.js";
import { program, loginCmd, genconfigCmd } from "./cli.js";

const noColor = process.env.NO_COLOR && process.env.NO_COLOR !== '';

if (noColor) chalk.level = 0;

program.version(pkgjson.version);
program.action(async function() {
  const token = await login();
  
  await render(
    <App openrouter={new OpenRouter({ apiKey: token })} />, 
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