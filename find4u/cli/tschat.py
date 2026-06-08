import json
import os
from rich.markdown import Markdown
from rich.console import Console
import time
import urllib.request
from urllib.error import HTTPError
import webbrowser

def login():
    if not os.path.isfile("textsynth-token.secret"):
        print("Looks like you haven't logged in. Please sign up to TextSynth and input your API token.")
        print("The webpage will open in 3 seconds...")
        time.sleep(3)
        webbrowser.open("https://textsynth.com/signup.html")
        token = input("Input your API token: ")
        with open("textsynth-token.secret", "w") as f:
            f.write(token)
        print("Logged in")
        return token
        
    with open("textsynth-token.secret") as f:
        print("Automatically logged in")
        return f.read()

def chat(msgs, tok, con):  
    req = urllib.request.Request(
        "https://api.textsynth.com/v1/engines/llama3.3_70B_instruct/chat"
    )
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Content-Type", f"text/json")
    req.data = json.dumps({
        "messages": msgs, 
        "stream": True, 
        "max_tokens": 200, 
        "system": "You are a helpful assistant. Don't swear. Don't be "
                  "overconfident, but don't be underconfident either. You only"
                  " have 200 tokens to spare. Therefore, try to get the point "
                  "across in that time."
    }).encode("utf-8")
    
    for retry in range(3):
        try:
            print("\x1b7", end="")
            full = ""
            with urllib.request.urlopen(req) as f:
                complete = False
                while not complete:
                    out = json.loads(f.readline().decode("utf-8"))
                    assistant = out["text"]
                    complete = out["reached_end"]
                    print("\x1b8", end="")
                    con.print(full.strip(), end="", soft_wrap=False)
                    full += assistant
                    f.readline()
            msgs.append(full)
            print()
            return
        except HTTPError as e:
            try:
                info = json.loads(e.fp.read().decode("utf-8"))["error"]
            except:
                info = "Failed to get info about error."
            if e.code == 498:
                con.print("[bold red]Oops, the request was blocked by a "
                          "CAPTCHA.[/bold red]")
                con.print("[bold red]Please click the 'Reset captcha counter' "
                          "button on the webpage that will open in 3 seconds...[/bold red]")
                time.sleep(3)
                webbrowser.open("https://textsynth.com/reset_captcha.html")
                con.input("[italic]Press ENTER to retry. [/italic]")
                return chat(msgs, tok, con)
            elif e.code == 429:
                wait = 5 * (2 ** retry)  # exponential backoff
                con.print(f"[bold yellow]Rate limited. Waiting {wait} seconds before retrying...[/bold yellow]")
                time.sleep(wait)
            else:
                con.print("[bold red]Oops, your message didn't go through. Wait a bit, then retry.[/bold red]")
                con.print(f"[bold red]{info} (HTTP error code {e.code}: {e.msg})[/bold red]")
                con.input("[italic]Press ENTER to retry. [/italic]")
                return chat(msgs, tok, con)
    con.print("[bold red]Too many retries, giving up.[/bold red]")
    msgs.append("[error: rate limit reached]")

def main():
    print("Welcome to TextSynth Chat Demo! This is yet another AI chat.")
    
    con = Console()
    
    tok = login()
    msgs = []
    while True:
        try:
            user = con.input("[dim]>> [/dim]")
            msgs.append(user)
            chat(msgs, tok, con)
        except KeyboardInterrupt:
            print("\nThanks for using TextSynth Chat Demo!")
            return
#
if __name__ == "__main__": main()