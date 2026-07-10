"use client";
import React from "react";

interface ToolBadgeProps {
  tool: string | null;
}

export default function ToolBadge({ tool }: ToolBadgeProps) {
  if (!tool) return null;
  
  let className = "tool-badge ";
  let icon = "";
  let label = "";

  if (tool.includes("document_search") && tool.includes("orders_database")) {
    className += "both-sources";
    icon = "🔀";
    label = "Hybrid Search";
  } else if (tool.includes("document_search") || tool === "search_documents") {
    className += "document-search";
    icon = "📄";
    label = "Document Search";
  } else if (tool.includes("orders_database") || tool === "query_orders") {
    className += "sql-query";
    icon = "🗃️";
    label = "SQL Query";
  } else {
    className += "document-search";
    icon = "🔧";
    label = tool;
  }

  return (
    <div className={className}>
      <span className="tool-badge-icon">{icon}</span>
      <span>{label}</span>
    </div>
  );
}
