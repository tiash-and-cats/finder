#!/usr/bin/env node
import React from 'react';
import App from "./app.js";
import login from "./login.js";
import fs from "fs/promises";
import { render } from "ink";
import { OpenRouter, tool } from '@openrouter/agent';
import { Command } from 'commander';
import { marked } from 'marked';
import { markedTerminal } from 'marked-terminal';

import pkgjson from "./package.json" with { type: "json" };
import { defaultConfig } from "./config.js";

const program = new Command();

program.name(process.env.npm_execpath?.includes('npx') ? 'npx find4u-cli' : 'find4u-cli');
program.description("Find4U CLI");
program.version(pkgjson.version);

program.action(async function() {
  marked.use(markedTerminal({
    reflowText: true,                          // Activates line wrapping
    width: (process.stdout.columns || 80) - 1  // Dynamically drops to terminal size
  }));

  const token = await login();

  process.stdout.write("\x1b[?1049h");

  try {
    await render(
      <App openrouter={new OpenRouter({ apiKey: token })} marked={marked} />, 
      { exitOnCtrlC: false }
    ).waitUntilExit();
    process.stdout.write("\x1b[?1049l");
    process.exit(0);
  } catch (e) {
    process.stdout.write("\x1b[?1049l");
    throw e;
  }
});

const loginCmd = program.command("login");
loginCmd.description("Log in. You usually don't need to run this as just " +
                     "running 'npx find4u-cli' automatically logs you in and " + 
                     "asks you to log in if you're not logged in. But this " +
                     "command is useful in case you need to force a login " +
                     "(npx find4u-cli login --force).")
loginCmd.option("--force", "Force a login. This makes you log in even if " +
                           "you're already logged in.");
loginCmd.action(async function(options) {
  await login(true, !!options.force);
});

const genconfigCmd = program.command("genconfig");
genconfigCmd.description("Generate a find4u.config.json");
genconfigCmd.action(async function() {
  await fs.writeFile("find4u.config.json", JSON.stringify(defaultConfig, null, 2), "utf-8");
  console.log("Successfully generated ./find4u.config.json");
});

program.parse();