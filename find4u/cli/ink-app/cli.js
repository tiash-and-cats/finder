import { Command } from 'commander';

const program = new Command();

program.name('npx find4u-cli');
program.description("Find4U CLI");

const loginCmd = program.command("login");
loginCmd.description("Log in. You usually don't need to run this as just " +
                     "running 'npx find4u-cli' automatically logs you in and " + 
                     "asks you to log in if you're not logged in. But this " +
                     "command is useful in case you need to force a login " +
                     "(npx find4u-cli login --force).");
loginCmd.option("--force", "Force a login. This makes you log in even if " +
                           "you're already logged in.");

const genconfigCmd = program.command("genconfig");
genconfigCmd.description("Generate a find4u.config.json");

export { program, loginCmd, genconfigCmd };