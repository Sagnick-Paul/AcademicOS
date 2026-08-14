import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DocumentCard } from "../DocumentCard";
import type { Document } from "@/types";

const baseDoc: Document = {
  id: "00000000-0000-0000-0000-000000000001",
  owner_id: "00000000-0000-0000-0000-000000000099",
  filename: "stored.pdf",
  original_filename: "my-notes.pdf",
  file_type: "pdf",
  file_size: 1024 * 1024 * 2.3,
  storage_path: "pdf/stored.pdf",
  upload_status: "ready",
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

describe("DocumentCard", () => {
  it("renders filename, type label, size, and upload date", () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} onRequestDelete={onRequestDelete} />);

    const card = screen.getByTestId("document-card");
    expect(card).toHaveAttribute("data-document-id", baseDoc.id);
    expect(within(card).getByText("my-notes.pdf")).toBeInTheDocument();
    expect(within(card).getByTestId("document-card-type")).toHaveTextContent("PDF");
    expect(within(card).getByTestId("document-card-size")).toHaveTextContent(/MB/);
    expect(within(card).getByTestId("document-card-date")).toHaveTextContent(/uploaded/i);
  });

  it("renders the upload status with a data attribute", () => {
    render(<DocumentCard document={{ ...baseDoc, upload_status: "failed" }} onRequestDelete={vi.fn()} />);
    const status = screen.getByTestId("document-card-status");
    expect(status).toHaveAttribute("data-status", "failed");
    expect(status).toHaveTextContent("Failed");
  });

  it("invokes onRequestDelete with the document when Delete is clicked", async () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} onRequestDelete={onRequestDelete} />);

    await userEvent.click(screen.getByTestId("document-card-delete"));

    expect(onRequestDelete).toHaveBeenCalledTimes(1);
    expect(onRequestDelete).toHaveBeenCalledWith(baseDoc);
  });

  it("disables the delete button while deleting is true", async () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} deleting onRequestDelete={onRequestDelete} />);

    const button = screen.getByTestId("document-card-delete");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/deleting/i);

    await userEvent.click(button);
    expect(onRequestDelete).not.toHaveBeenCalled();
  });
});