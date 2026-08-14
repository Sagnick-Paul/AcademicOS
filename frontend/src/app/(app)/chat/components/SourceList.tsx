"use client";

import { useState } from "react";
import type { ChatMessageSource } from "@/types";
import styles from "./SourceList.module.css";

interface SourceListProps {
  sources: readonly ChatMessageSource[];
  /** Map from document_id to the user's filename for that document. */
  documentTitles: ReadonlyMap<string, string>;
}

/**
 * Renders the citations attached to an assistant message as a
 * collapsible list. Visually secondary to the answer text — the
 * default state is collapsed so the assistant reply reads cleanly,
 * with a "Sources (N)" affordance to expand.
 *
 * Uses real backend fields only: `position`, `document_title`
 * (resolved by the parent), `page_number`, and `snippet`. We do
 * not invent document names or page numbers.
 */
export function SourceList({ sources, documentTitles }: SourceListProps) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <section
      className={styles.root}
      aria-label="Cited sources"
      data-testid="chat-source-list"
    >
      <button
        type="button"
        className={styles.toggle}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        data-testid="chat-source-toggle"
      >
        <span className={styles.toggleLabel}>
          {expanded ? "Hide sources" : "Sources"} ({sources.length})
        </span>
        <span className={styles.toggleIcon} aria-hidden="true">
          {expanded ? "−" : "+"}
        </span>
      </button>

      {expanded ? (
        <ol className={styles.list} data-testid="chat-source-items">
          {sources.map((src) => {
            const title = src.document_id
              ? documentTitles.get(src.document_id) ?? null
              : null;
            return (
              <li
                key={src.id}
                className={styles.item}
                data-testid="chat-source-item"
              >
                <div className={styles.itemHeader}>
                  <span className={styles.itemIndex}>[{src.position}]</span>
                  <span className={styles.itemTitle} title={title ?? undefined}>
                    {title ?? "Untitled document"}
                  </span>
                </div>
                <div className={styles.itemMeta}>
                  {src.page_number != null ? (
                    <span className={styles.itemMetaItem}>
                      Page {src.page_number}
                    </span>
                  ) : null}
                  {src.score != null ? (
                    <span className={styles.itemMetaItem}>
                      Score {src.score.toFixed(2)}
                    </span>
                  ) : null}
                </div>
                {src.snippet ? (
                  <p className={styles.snippet}>{src.snippet}</p>
                ) : null}
              </li>
            );
          })}
        </ol>
      ) : null}
    </section>
  );
}
