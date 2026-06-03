import json
import os
from rich.markdown import Markdown
from rich.console import Console
import textwrap
import time
import urllib.request
from urllib.error import HTTPError
import webbrowser

def login():
    if not os.path.isfile("openrouter-token.secret"):
        print("Looks like you haven't logged in. Please sign up to OpenRouter, "
              "create an API key and input it here.")
        print("The webpage will open in 3 seconds...")
        time.sleep(3)
        webbrowser.open("https://openrouter.ai")
        token = input("Input your API token: ")
        with open("openrouter-token.secret", "w") as f:
            f.write(token)
        print("Logged in")
        return token
        
    with open("openrouter-token.secret") as f:
        print("Automatically logged in")
        return f.read()

def chat(msgs, tok, con, retries=3):
    url = "https://openrouter.ai/api/v1/chat/completions"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Content-Type", "application/json")

    payload = {
        "model": "openrouter/free",
        "messages": msgs,
        "stream": True
    }
    req.data = json.dumps(payload).encode("utf-8")

    for attempt in range(retries):
        try:
            full = ""
            buffer = ""
            with urllib.request.urlopen(req) as f:
                for raw_line in f:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            msgs.append({"role":"assistant","content":full})
                            print()
                            return
                        try:
                            data_obj = json.loads(data)
                            delta = data_obj["choices"][0]["delta"].get("content")
                            if delta:
                                full += delta
                                with con.capture() as cap:
                                    con.print(Markdown(full.strip()))
                                print("\x1bc" + cap.get(), end="", flush=True)
                        except json.JSONDecodeError:
                            pass
        except HTTPError as e:
            if e.code == 429:
                wait = 5 * (2 ** attempt)
                con.print(f"[bold yellow]Rate limited. Waiting {wait} seconds "
                          f"before retrying...[/bold yellow]")
                time.sleep(wait)
            else:
                try:
                    info = json.loads(e.read().decode("utf-8")).get("error", "Unknown error")
                except:
                    info = "Failed to get info about error."
                con.print("[bold red]Oops, your message didn't go through.[/bold red]")
                con.print(f"[bold red]{info} (HTTP error code {e.code}: {e.reason})[/bold red]")
                con.input("[italic]Press ENTER to retry. [/italic]")
                return chat(msgs, tok, con)
    con.print("[bold red]Too many retries, giving up.[/bold red]")
    msgs.append({"role": "assistant", "content": "[error: rate limit reached]"})

def main():
    print("Welcome to OpenRouter Chat Demo! This is yet another AI chat.")
    
    con = Console(width=os.get_terminal_size().columns - 2)
    
    tok = login()
    msgs = []
    while True:
        try:
            user = con.input("[dim]>> [/dim]")
            msgs.append({"role":"user","content":user})
            chat(msgs, tok, con)
        except KeyboardInterrupt:
            print("\nThanks for using OpenRouter Chat Demo!")
            return
#
if __name__ == "__main__": main()