"use client";
import { useState, useEffect, useRef } from "react";
import { sanitize } from "@markdown-design/markdown-it-sanitize";
import escapeHtml from 'escape-html';
import markdownit from "markdown-it";
import Head from "next/head";
import hljs from "highlight.js";
import "highlight.js/styles/default.css";
import "./chat.css";

function CTA() {
  const ctas = [
    "What's on your mind today?",
    "Type a message and I'll jump in.",
    "Got a question? I've got answers.",
    "Your thoughts go here...",
    "Ask me anything — big or small.",
    "Ready when you are.",
    "Start typing to wake me up.",
    "Looking for something? Let's find it together.",
    "Say hello, I don't bite.",
    "The chat begins with you."
  ];

  // Always render a stable default during SSR
  const [cta, setCta] = useState(ctas[0]);

  // Randomize only after hydration
  useEffect(() => {
    setCta(ctas[Math.floor(Math.random() * ctas.length)]);
  }, []);

  return (
    <div id="cta">
      <img src="/find4u/logo.svg" alt="Find4U logo" width={50} />
      <p>I'm Find4U, your AI assistant.</p>
      <p>{cta}</p>
    </div>
  );
}

function ChatBox({ messages }) {
  const md = useRef(
    markdownit({
      html: true,
      highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
          try {
            return `<pre class="hljs"><code>` +
              hljs.highlight(str, { language: lang }).value +
              `</code></pre>`;
          } catch (__) {}
        }
        return `<pre class="hljs"><code>` + escapeHtml(str) + `</code></pre>`;
      }
    }).use(sanitize)
  );
  return (
    <>
      <div id="chat">
        {messages.map((m, i) => 
          m.role === "user" ? (
            <div key={i} className="msg">
              <p>{m.content}</p>
            </div>
          ) : (
            <div key={i}
              dangerouslySetInnerHTML={{ __html: md.current.render(m.content) }}
            />
          )
        )}
        <br />
      </div>
    </>
  );
}

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [disabled, setDisabled] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim()) return;

    setDisabled(true);
    const newMessages = [...messages, { role: "user", content: input }, { role: "assistant", content: "*Thinking...*" }];
    setMessages(newMessages);
    setInput("");

    function failSafe(msg) {
      let assistantMsg = { role: "assistant", content: `<p style="color: red">${escapeHtml(msg)}</p>` };
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = assistantMsg;
        return updated;
      });
      setDisabled(false);
    }

    let res;
    try {
      res = await fetch("/find4u/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newMessages }),
      });
      if (!res.ok) {
        return failSafe(await res.text());
      }
    } catch (e) {
      return failSafe("Oops! There's been a problem on the backend. Try retrying the message.");
    }

    let assistantMsg = { role: "assistant", content: "" };
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = assistantMsg;
      return updated;
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      assistantMsg.content += decoder.decode(value, { stream: true });
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = assistantMsg;
        return updated;
      });
    }
    setDisabled(false);
  }

  useEffect(() => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <>
      {messages.length > 0 ? <ChatBox messages={messages} /> : <CTA />}

      <form id="msgadd" onSubmit={handleSubmit}>
        <input
          name="msg"
          type="text"
          autoComplete="off"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={disabled}>Send</button>
      </form>
    </>
  );
}