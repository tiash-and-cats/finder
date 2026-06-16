import { NextResponse } from "next/server";
import { OpenRouter } from "@openrouter/agent";

const openrouter = new OpenRouter({
  apiKey: JSON.parse(process.env.OPENROUTER_KEY),
});

export async function POST(req) {
  const { messages } = await req.json();

  let result;
  try {
    result = await openrouter.callModel({
      model: "openrouter/free",
      instructions: "You are a helpful AI assistant called Find4U.",
      input: messages
    });
  } catch (e) {
    return new Response(e.error.message, {
      headers: { "Content-Type": "text/plain" },
      status: e.error.code,
    });
  }

  // Stream response back to client
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      for await (const delta of result.getTextStream()) {
        controller.enqueue(encoder.encode(delta));
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "text/plain" },
  });
}