"use client";

import React, { useRef, useEffect } from "react";

interface InputBarProps {
  onSend: (message: string) => void;
  disabled: boolean;
  isStreaming: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function InputBar({ onSend, disabled, isStreaming, value, onChange }: InputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (value.trim() && !disabled) {
      onSend(value.trim());
      onChange("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  };

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  return (
    <div className="input-bar-container">
      <form onSubmit={handleSubmit} className="input-bar">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask about policies, orders, or anything..."
            className="input-field"
            rows={1}
          />
        </div>
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className="send-button"
        >
          {isStreaming ? (
            <div className="send-button-spinner" />
          ) : (
            <span className="send-button-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: "translateX(2px) translateY(-1px)" }}>
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </span>
          )}
        </button>
      </form>
    </div>
  );
}
