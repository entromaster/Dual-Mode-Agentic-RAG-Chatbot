"use client";

import React, { useState } from "react";
import ToolBadge from "./ToolBadge";

interface MessageBubbleProps {
  message: {
    id: string;
    role: "user" | "assistant";
    content: string;
    toolUsed?: string | null;
    citations?: string[];
    sqlQuery?: string;
    isStreaming?: boolean;
    isError?: boolean;
    error?: string;
  };
}

function formatContent(text: string) {
  if (!text) return null;

  const parts = text.split(/(```[\s\S]*?```)/g);
  
  return parts.map((part, index) => {
    if (part.startsWith("```") && part.endsWith("```")) {
      const code = part.slice(3, -3).replace(/^[a-z]+\n/, "");
      return (
        <pre key={index}>
          <code>{code}</code>
        </pre>
      );
    }
    
    let formatted = part;
    const boldParts = formatted.split(/(\*\*.*?\*\*)/g);
    
    return (
      <span key={index}>
        {boldParts.map((bp, i) => {
          if (bp.startsWith("**") && bp.endsWith("**")) {
            return <strong key={i}>{bp.slice(2, -2)}</strong>;
          }
          return bp.split('\n').map((line, j, arr) => (
            <React.Fragment key={`${i}-${j}`}>
              {line}
              {j < arr.length - 1 && <br />}
            </React.Fragment>
          ));
        })}
      </span>
    );
  });
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [showSql, setShowSql] = useState(false);
  const [showCitations, setShowCitations] = useState(false);

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      {!isUser && (
        <div className="bot-avatar">🤖</div>
      )}
      
      <div className={`message-bubble ${isUser ? "user-bubble" : "bot-bubble"}`}>
        {!isUser && message.toolUsed && (
          <ToolBadge tool={message.toolUsed} />
        )}

        <div className="message-content">
          {message.error || message.isError ? (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {message.error || message.content}
            </div>
          ) : (
            formatContent(message.content)
          )}
          {message.isStreaming && <span className="streaming-cursor" />}
        </div>

        {/* Citations Section */}
        {message.citations && message.citations.length > 0 && (
          <div className="citations-section">
            <button 
              onClick={() => setShowCitations(!showCitations)}
              className="citations-toggle"
            >
              <span className={`citations-toggle-arrow ${showCitations ? 'expanded' : ''}`}>▶</span>
              {message.citations.length} Sources Used
            </button>
            {showCitations && (
              <div className="citations-list">
                {message.citations.map((cite, idx) => (
                  <div key={idx} className="citation-pill">
                    <span className="citation-pill-icon">📄</span>
                    <span>{cite}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SQL Query Section */}
        {message.sqlQuery && (
          <div className="sql-section">
            <button 
              onClick={() => setShowSql(!showSql)}
              className="sql-toggle"
            >
              <span className={`sql-toggle-arrow ${showSql ? 'expanded' : ''}`}>▶</span>
              View SQL Query
            </button>
            {showSql && (
              <div className="sql-code-block">
                <span className="sql-label">SQLite</span>
                <pre>
                  <code>{message.sqlQuery}</code>
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
