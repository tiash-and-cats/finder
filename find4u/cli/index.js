import { OpenRouter, tool } from '@openrouter/agent';
import { marked } from 'marked';
import { markedTerminal } from 'marked-terminal';
import { exec } from "child_process";
import { z } from "zod";
import os from "os";
import colors from 'ansi-colors';
import fs from "fs";
import readline from "readline";
import open from "open";
import yoctoSpinner from 'yocto-spinner';

function input(rl, prompt) {
  return new Promise(resolve => rl.question(prompt, resolve));
}

async function login(rl) {
  const tokenFile = "openrouter-token.secret";
  if (!fs.existsSync(tokenFile)) {
    console.log("Looks like you haven't logged in. Please sign up to OpenRouter, create an API key and input it here.");
    console.log("The webpage will open in 3 seconds...");
    await new Promise(r => setTimeout(r, 3000));
    await open("https://openrouter.ai");

    const token = await input(rl, "Enter your API token: ");

    fs.writeFileSync(tokenFile, token);
    console.log("Logged in");
    return token;
  } else {
    console.log("Automatically logged in");
    return fs.readFileSync(tokenFile, "utf-8").trim();
  }
}

function formatDuration(duration) {
  const totalSeconds = duration.total('seconds');
  if (totalSeconds <= 0) return "already reset";

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  let parts = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (seconds && !hours) parts.push(`${seconds}s`); // only show seconds if <1h

  return parts.join(" ");
}

function runTerminalCommand(command) {
  return new Promise((resolve) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        resolve([true, `Error: ${error.message}\nStderr: ${stderr}`]);
      } else {
        resolve([false, stdout || stderr || "Command completed successfully with no output."]);
      }
    });
  });
}

async function chat(rl, msgs, openrouter) {
  try {
    const payload = {
      model: 'openrouter/free',
      input: msgs,
      tools: [
        tool({
          name: "execute_command",
          description: `Runs a specific ${os.platform() == "win32" ? "Windows command prompt" : "shell"} command on the host computer and returns the output.`,
          inputSchema: z.object({
            command: z.string().describe(`The exact ${os.platform() == "win32" ? "Windows command prompt" : "shell"} command to execute.`),
          }),
          execute: async ({ command }) => {
            const confirmation = await input(rl, colors.bold(`Agent wants to execute command ${colors.blue(command)}, allow? (y/n) `));

            if (confirmation.toLowerCase() === "y") {
              process.stdout.write("\x1bM\r");
              const spinner = yoctoSpinner({text: colors.italic.dim("Running: ") + colors.bold.blue(command)}).start();
              const [error, output] = await runTerminalCommand(command);
              if (error) {
                spinner.error();
              } else {
                spinner.success();
              }
              return { output };
            } else {
              return { output: "Permission Denied: The user blocked execution of this command." };
            }
          },
        }),
      ],
    };
    const result = openrouter.callModel(payload);
    let full = "";
    for await (const delta of result.getTextStream()) {
      full += delta;
      const rendered = marked(full);
      process.stdout.write("\x1bc" + rendered);
    }
  } catch (e) {
    if (!e.error) throw e;
    if (e.error.code === 429) {
      if (e.error.metadata.retry_after_seconds) {
        console.log(colors.bold.yellow(`Rate limited, trying again in ${
          e.error.metadata.retry_after_seconds
        } seconds...`));
        await new Promise(
          r => setTimeout(r, e.error.metadata.retry_after_seconds * 1000)
        );
        return chat(rl, msgs, openrouter);
      }
      const resetHeader = e.error.metadata.headers['X-RateLimit-Reset'];
      const resetInstant = Temporal.Instant.fromEpochMilliseconds(parseInt(resetHeader, 10));
      const now = Temporal.Now.instant();
      const duration = resetInstant.since(now, {smallestUnit: "nanoseconds"});

      // Convert to local time zone for display
      const resetLocal = resetInstant.toZonedDateTimeISO(Temporal.Now.timeZoneId());

      console.log(colors.bold.yellow(
        `Rate limited, try again on ${resetLocal.toLocaleString("en-US", { 
          dateStyle: "full", 
          timeStyle: "long" 
         })} ` +
        `(in ${formatDuration(duration)})`
      ));
      console.log(colors.bold.yellow(e.error.message));
    } else {
      throw e;
    }
  }
}

async function main() {
  const msgs = [];
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  marked.use(markedTerminal({
    reflowText: true,
    width: process.stdout.columns || 80,
    
    heading: colors.bold.magenta,
    code: colors.bold.cyan,
    codespan: colors.bold.cyan,
    tableOptions: { 
      colWidths: Array(4).fill(((process.stdout.columns || 80) - 8) / 4), 
                 // assuming Find4U generates at most 4-col tables. hoping it does
      wordWrap: true,
      
      style: {
        head: ["cyan"]
      }
    }
  }));
  
  console.log("Welcome to OpenRouter Chat Demo! This is yet another AI chat.");
  
  const openrouter = new OpenRouter({
    apiKey: await login(rl)
  });

  while (true) {
    msgs.push({ role: "user", content: await input(rl, ">> ") });
    await chat(rl, msgs, openrouter);
  }
}

main();