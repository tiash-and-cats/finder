const { configSchema } = await import("../find4u/cli/ink-app/config-schema.js");

console.log(JSON.stringify(configSchema.toJSONSchema()));