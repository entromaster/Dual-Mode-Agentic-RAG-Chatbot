"use client";

import React, { useRef, useEffect, useCallback } from "react";
import type { ChatMessage } from "@/app/page";
import MessageBubble from "./MessageBubble";

/* ── Suggested questions for welcome state ──────────────────────── */
const SUGGESTIONS = [
  {
    icon: "📋",
    text: "What is the return policy for electronics?",
  },
  {
    icon: "📦",
    text: "Show me the top 5 most expensive products in stock",
  },
  {
    icon: "👤",
    text: "Which customers have placed the most orders?",
  },
  {
    icon: "🚚",
    text: "What are the shipping guidelines for fragile items?",
  },
  {
    icon: "💰",
    text: "What was the total revenue last quarter by category?",
  },
  {
    icon: "📄",
    text: "Summarize the employee handbook leave policies",
  },
];

interface ChatWindowProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSuggestionClick?: (text: string) => void;
}

export default function ChatWindow({
  messages,
  isStreaming,
  onSuggestionClick,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll on new content */
  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* ── Welcome state ─────────────────────────────────────────── */
  if (messages.length === 0) {
    return (
      <div className="chat-window" ref={containerRef}>
        <div className="welcome-container">
          <div className="welcome-icon" aria-hidden="true">
            ✨
          </div>
          <h2 className="welcome-title">
            How can I help you today?
          </h2>
          <p className="welcome-subtitle">
            I can search company documents, query databases, or combine both to
            answer your questions about Northwind Gadgets.
          </p>
          <div className="welcome-suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                className="suggestion-card"
                onClick={() => onSuggestionClick?.(s.text)}
                type="button"
              >
                <span className="suggestion-icon">{s.icon}</span>
                <span className="suggestion-text">{s.text}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  /* ── Message list ──────────────────────────────────────────── */
  return (
    <div className="chat-window" ref={containerRef}>
      <div className="chat-messages">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Typing indicator (only when last bot message is streaming and empty) */}
        {isStreaming &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "assistant" &&
          messages[messages.length - 1].content === "" && (
            <div className="typing-indicator">
              <div className="bot-avatar" aria-hidden="true">
                🤖
              </div>
              <div className="typing-bubble">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
