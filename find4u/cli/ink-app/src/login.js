import os from "os";
import fs from "fs/promises";
import { existsSync } from 'node:fs';
import inquirer from 'inquirer';
import open from "open";

export default async function login() {
  const tokenFile = os.homedir() + "/.find4u-token.secret";
  if (!existsSync(tokenFile)) {
    console.log("Looks like you haven't logged in. Please sign up to OpenRouter, create an API key and input it here.");
    console.log("The webpage will open in 3 seconds...");
    await new Promise(r => setTimeout(r, 3000));
    await open("https://openrouter.ai");

    const token = (await inquirer.prompt([{
      type: 'password',
      name: 'token',
      message: 'Enter your OpenRouter API key:',
      mask: "*"
    }])).token;

    await fs.writeFile(tokenFile, token);
    console.log("Logged in");
    return token;
  } else {
    console.log("Automatically logged in");
    return (await fs.readFile(tokenFile, "utf-8")).trim();
  }
}