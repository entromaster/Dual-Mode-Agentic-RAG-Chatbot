"use client";

import React, { useState, useCallback } from "react";
import ChatWindow from "@/components/ChatWindow";
import InputBar from "@/components/InputBar";

/* ── Types ──────────────────────────────────────────────────────── */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolUsed?: string;
  citations?: string[];
  sqlQuery?: string;
  isStreaming?: boolean;
  isError?: boolean;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ── Page Component ─────────────────────────────────────────────── */
export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [inputValue, setInputValue] = useState("");

  /* Build compact history payload */
  const buildHistory = useCallback(
    (msgs: ChatMessage[]) =>
      msgs
        .filter((m) => !m.isError)
        .map((m) => ({ role: m.role, content: m.content })),
    [],
  );

  /* ── Send message & stream SSE response ────────────────────── */
  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
      };

      /* Placeholder for the assistant reply */
      const botId = crypto.randomUUID();
      const botMsg: ChatMessage = {
        id: botId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);

      try {
        const history = buildHistory(messages);
        const response = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim(), history }),
        });

        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();

        let buffer = "";
        let accContent = "";
        let accTool: string | undefined;
        const accCitations: string[] = [];
        let accSql: string | undefined;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          /* Process complete SSE lines */
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? ""; // keep incomplete last line

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data: ")) continue;

            const payload = trimmed.slice(6); // strip "data: "

            try {
              const event = JSON.parse(payload);

              switch (event.type) {
                case "token":
                  accContent += event.content ?? "";
                  break;
                case "tool_used":
                  accTool = event.tool ?? event.content;
                  break;
                case "citation":
                  if (event.source) accCitations.push(event.source);
                  else if (event.content) accCitations.push(event.content);
                  break;
                case "sql_query":
                  accSql = event.query ?? event.content;
                  break;
                case "error":
                  accContent += `\n\n⚠️ ${event.message ?? event.content ?? "An error occurred."}`;
                  break;
                case "done":
                  break;
                default:
                  /* Unknown event — try treating as token */
                  if (event.content) accContent += event.content;
              }
            } catch {
              /* Not JSON — might be a raw token string */
              if (payload !== "[DONE]") accContent += payload;
            }

            /* Update message in-place */
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? {
                      ...m,
                      content: accContent,
                      toolUsed: accTool ?? m.toolUsed,
                      citations:
                        accCitations.length > 0
                          ? [...accCitations]
                          : m.citations,
                      sqlQuery: accSql ?? m.sqlQuery,
                      isStreaming: true,
                    }
                  : m,
              ),
            );
          }
        }

        /* Finalise bot message */
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? {
                  ...m,
                  content: accContent || "I couldn't generate a response. Please try again.",
                  toolUsed: accTool,
                  citations:
                    accCitations.length > 0 ? [...accCitations] : undefined,
                  sqlQuery: accSql,
                  isStreaming: false,
                }
              : m,
          ),
        );
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? {
                  ...m,
                  content: `Sorry, I couldn't connect to the server. ${errorMessage}`,
                  isStreaming: false,
                  isError: true,
                }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, messages, buildHistory],
  );

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-logo" aria-hidden="true">
            🤖
          </div>
          <div className="header-text">
            <h1>Northwind Gadgets AI</h1>
            <p>Dual-mode Agentic RAG Assistant</p>
          </div>
          <div className="header-status">
            <span className="status-dot" />
            <span>Online</span>
          </div>
        </div>
      </header>

      {/* Chat area */}
      <ChatWindow 
        messages={messages} 
        isStreaming={isStreaming} 
        onSuggestionClick={setInputValue}
      />

      {/* Input */}
      <InputBar
        onSend={handleSend}
        disabled={isStreaming}
        isStreaming={isStreaming}
        value={inputValue}
        onChange={setInputValue}
      />
    </div>
  );
}
