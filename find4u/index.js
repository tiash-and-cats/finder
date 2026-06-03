import { OpenRouter } from '@openrouter/agent';
import { marked } from 'marked';
import { markedTerminal } from 'marked-terminal';
import colors from 'ansi-colors';
import fs from "fs";
import readline from "readline";
import open from "open";

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

async function chat(msgs, openrouter) {
  try {
    const result = openrouter.callModel({
      model: 'openrouter/free',
      input: msgs,
    });
    let full = "";
    for await (const delta of result.getTextStream()) {
      full += delta;
      const rendered = marked(full);
      process.stdout.write("\x1bc" + rendered);
    }
  } catch (e) {
    if (e.error.code === 429) {
      if (e.error.metadata.retry_after_seconds) {
        console.log(colors.bold.yellow(`Rate limited, trying again in ${
          e.error.metadata.retry_after_seconds
        } seconds...`));
        await new Promise(
          r => setTimeout(r, e.error.metadata.retry_after_seconds * 1000)
        );
        return chat(msgs, openrouter);
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
  marked.use(markedTerminal());
  
  console.log("Welcome to OpenRouter Chat Demo! This is yet another AI chat.");
  
  const openrouter = new OpenRouter({
    apiKey: await login(rl)
  });

  while (true) {
    msgs.push({ role: "user", content: await input(rl, ">> ") });
    await chat(msgs, openrouter);
  }
}

main();