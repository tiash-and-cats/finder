import React from 'react';
import { useState, useEffect, useRef } from 'react';
import { Box, Text, Newline, useStdout, useApp } from 'ink';
import { TextInput, Alert } from '@inkjs/ui';

import asciiArt from "./splash.json" with { type: "json" };
import getTools from "./tools.js";

const configuredTools = [];

function Splash({ art }) {
  return (
    <>
      {art.map((line, i) => (
        <Text key={i}>{line}</Text>
      ))}
    </>
  );
}

function ChatBox({ messages, marked }) {
  return (
    <>
      {messages.map((m, i) => 
        m.role === "user" ? (
          <Box padding={1} paddingLeft={1}>
            <Text color="cyan" bold={true}> &gt; </Text>
            <Text dimColor={true}>{m.content}</Text>
          </Box>
        ) : m.role === "action" ? (
          <Box flexShrink={1}><Alert variant={m.type}>{m.content}</Alert></Box>
        ) : (
          <Box flexDirection="column" paddingX={1}>
            {marked(m.content).split("\n").map(x => <Text>{x}</Text>)}
          </Box>
        )
      )}
      <Newline />
    </>
  );
}

const Clear = () => <Text>{"\x1bc\x1b[H"}</Text>;

export default function App({ openrouter, marked }) {
  // Use Ink's built-in hook to safely grab the stdout stream
  const { stdout } = useStdout();
  
  // Track both dimensions for safer grid control
  const [dimensions, setDimensions] = useState({
    rows: stdout?.rows || 25,
    columns: stdout?.columns || 80
  });

  useEffect(() => {
    if (!stdout || !stdout.isTTY) return;

    // Sync initial size safely
    setDimensions({ rows: stdout.rows, columns: stdout.columns });

    const handleResize = () => {
      setDimensions({ rows: stdout.rows, columns: stdout.columns });
    };

    // Attach listener to Ink's managed stream
    stdout.on('resize', handleResize);

    // CRITICAL: Clean up the event listener on unmount
    return () => {
      stdout.off('resize', handleResize);
    };
  }, [stdout]);
  
  const [inputKey, setInputKey] = useState(0);
  const [messages, setMessages] = useState([]);
  
  const tools = useRef(getTools(messages, setMessages));

  const [disabled, setDisabled] = useState(false);
  
  const { exit } = useApp();

  async function onSubmit(msg) {
    if (msg === "/exit") {
      exit("Exited");
    }
    
    setInputKey(inputKey + 1);
    setDisabled(true);
    
    const newMessages = [...messages, { role: "user", content: msg }, { role: "assistant", content: "" }];
    setMessages(newMessages);
    
    const result = await openrouter.callModel({
      model: 'openrouter/free',
      instructions: "You are a helpful AI assistant called Find4U.",
      input: newMessages.slice(0, newMessages.length).filter(msg => msg.role != "action"),
      tools: tools.current
    });
    
    let assistantMsg = { role: "assistant", content: "" };
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = assistantMsg;
      return updated;
    });
    for await (const delta of result.getTextStream()) {
      assistantMsg.content += delta;
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = assistantMsg;
        return updated;
      });
    }
    
    setDisabled(false);
  }
  
  return (
    <>
      <Clear />
      <Box 
        minHeight={dimensions.rows} 
        width={dimensions.columns} 
        flexDirection="column"
      >
        <Box flexGrow={1} flexDirection="column">
          <Splash art={asciiArt} />
          <ChatBox messages={messages} marked={marked} />
        </Box>
        <Box borderStyle="round" borderDimColor={true}>
          <Text color="cyan" bold={true}> &gt; </Text>
          <TextInput key={inputKey} placeholder={disabled ? "Wait for Find4U to finish" : "Ask anything..."}
                     defaultValue="" onSubmit={onSubmit} isDisabled={disabled} />
        </Box>
      </Box>
    </>
  );
}