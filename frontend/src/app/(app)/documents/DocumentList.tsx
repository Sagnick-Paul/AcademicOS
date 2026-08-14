"use client";

import { DocumentCard } from "./DocumentCard";
import type { Document } from "@/types";
import styles from "./DocumentList.module.css";

interface DocumentListProps {
  documents: readonly Document[];
  /** Set of document IDs that are currently being deleted. */
  deletingIds: ReadonlySet<string>;
  onRequestDelete: (document: Document) => void;
}

/**
 * Renders the user's documents as a stack of cards. Pure presentational;
 * the parent owns the data and delete lifecycle.
 */
export function DocumentList({ documents, deletingIds, onRequestDelete }: DocumentListProps) {
  return (
    <ul className={styles.list} aria-label="Your documents" data-testid="document-list">
      {documents.map((document) => (
        <li key={document.id} className={styles.item}>
          <DocumentCard
            document={document}
            deleting={deletingIds.has(document.id)}
            onRequestDelete={onRequestDelete}
          />
        </li>
      ))}
    </ul>
  );
}