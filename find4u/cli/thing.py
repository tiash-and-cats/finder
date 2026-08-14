import syssys.path.append(r"E:\clones\randomx")import smolurl, jsonreq = smolurl.Request("https://openrouter.ai/api/v1/chat/completions")with open("openrouter-token.secret") as f: req.headers["Authorization"] = f"Bearer {f.read()}"
req.headers["Content-Type"] = "application/json"req.data = json.dumps({"model":"openrouter/free","messages":[{"role":"user","content":"hi"}],"stream":True})
req.method = "POST"

async def main():    async with smolurl.make_sse_stream(req) as stream:        stream.on("message", lambda msg: print("Got message:", msg))        stream.on("error", lambda err: print("Error:", err))        stream.ondefault = lambda evt, payload: print(f"Unhandled {evt}: {payload}")        await stream.loop()
#
import asyncio
asyncio.run(main())