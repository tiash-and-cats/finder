from django.shortcuts import render
from .utils import get_similar_docs, generate_reply

# views.py
def chat(request):
    msg = request.GET.get("msg")
    reply = "Hello! What would you like to chat about?"

    if msg:
        history = request.session.get("history", [])
        history.append({"role": "user", "content": msg})

        docs = get_similar_docs(msg, top_k=3)
        reply_text = generate_reply(msg, docs)
        history.append({"role": "bot", "content": reply_text})

        request.session["history"] = history[-5:]  # keep last 5 exchanges
        reply = reply_text

    return render(request, "chat.html", {"reply": reply})