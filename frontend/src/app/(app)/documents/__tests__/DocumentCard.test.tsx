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
  course_id: null,
  document_type: null,
  document_metadata: null,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

describe("DocumentCard", () => {
  it("renders filename, type label, size, and upload date", () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} onRequestDelete={onRequestDelete} onRequestEdit={vi.fn()} />);

    const card = screen.getByTestId("document-card");
    expect(card).toHaveAttribute("data-document-id", baseDoc.id);
    const titleLink = within(card).getByTestId("document-card-title-link");
    expect(titleLink).toHaveTextContent("my-notes.pdf");
    expect(titleLink).toHaveAttribute("href", `/documents/${baseDoc.id}`);
    expect(within(card).getByTestId("document-card-type")).toHaveTextContent("PDF");
    expect(within(card).getByTestId("document-card-size")).toHaveTextContent(/MB/);
    expect(within(card).getByTestId("document-card-date")).toHaveTextContent(/uploaded/i);
  });

  it("renders the upload status with a data attribute", () => {
    render(<DocumentCard document={{ ...baseDoc, upload_status: "failed" }} onRequestDelete={vi.fn()} onRequestEdit={vi.fn()} />);
    const status = screen.getByTestId("document-card-status");
    expect(status).toHaveAttribute("data-status", "failed");
    expect(status).toHaveTextContent("Failed");
  });

  it("invokes onRequestDelete with the document when Delete is clicked", async () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} onRequestDelete={onRequestDelete} onRequestEdit={vi.fn()} />);

    await userEvent.click(screen.getByTestId("document-card-delete"));

    expect(onRequestDelete).toHaveBeenCalledTimes(1);
    expect(onRequestDelete).toHaveBeenCalledWith(baseDoc);
  });

  it("disables the delete button while deleting is true", async () => {
    const onRequestDelete = vi.fn();
    render(<DocumentCard document={baseDoc} deleting onRequestDelete={onRequestDelete} onRequestEdit={vi.fn()} />);

    const button = screen.getByTestId("document-card-delete");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/deleting/i);

    await userEvent.click(button);
    expect(onRequestDelete).not.toHaveBeenCalled();
  });

  it("invokes onRequestEdit with the document when Edit is clicked", async () => {
    const onRequestEdit = vi.fn();
    render(<DocumentCard document={baseDoc} onRequestDelete={vi.fn()} onRequestEdit={onRequestEdit} />);

    await userEvent.click(screen.getByTestId("document-card-edit"));

    expect(onRequestEdit).toHaveBeenCalledTimes(1);
    expect(onRequestEdit).toHaveBeenCalledWith(baseDoc);
  });

  it("shows course label from courseLookup when course_id is present", () => {
    const docWithCourse = {
      ...baseDoc,
      course_id: "cc000000-0000-0000-0000-000000000001",
    };
    const lookup = new Map([["cc000000-0000-0000-0000-000000000001", "Electric Circuits"]]);
    render(
      <DocumentCard
        document={docWithCourse}
        courseLookup={lookup}
        onRequestDelete={vi.fn()}
        onRequestEdit={vi.fn()}
      />,
    );

    const courseBadge = screen.getByTestId("document-card-course");
    expect(courseBadge).toHaveTextContent("Electric Circuits");
    expect(courseBadge).toHaveAttribute("data-empty", "false");
  });

  it("shows 'Uncoursed' when course_id is null", () => {
    render(
      <DocumentCard
        document={baseDoc}
        onRequestDelete={vi.fn()}
        onRequestEdit={vi.fn()}
      />,
    );

    const courseBadge = screen.getByTestId("document-card-course");
    expect(courseBadge).toHaveTextContent("Uncoursed");
    expect(courseBadge).toHaveAttribute("data-empty", "true");
  });

  it("shows the document type label when document_type is present", () => {
    const docWithType = { ...baseDoc, document_type: "lecture_notes" as const };
    render(
      <DocumentCard document={docWithType} onRequestDelete={vi.fn()} onRequestEdit={vi.fn()} />,
    );

    const typeBadge = screen.getByTestId("document-card-document-type");
    expect(typeBadge).toHaveTextContent("Lecture Notes");
    expect(typeBadge).toHaveAttribute("data-empty", "false");
  });

  it("shows 'Untyped' when document_type is null", () => {
    render(
      <DocumentCard document={baseDoc} onRequestDelete={vi.fn()} onRequestEdit={vi.fn()} />,
    );

    const typeBadge = screen.getByTestId("document-card-document-type");
    expect(typeBadge).toHaveTextContent("Untyped");
    expect(typeBadge).toHaveAttribute("data-empty", "true");
  });

  it("shows author and subject from document_metadata when present", () => {
    const docWithMeta = {
      ...baseDoc,
      document_metadata: {
        author: "Jane Smith",
        subject: "Physics",
        semester: null,
        academic_year: null,
        tags: ["important", "exam-prep"],
      },
    };
    render(
      <DocumentCard document={docWithMeta} onRequestDelete={vi.fn()} onRequestEdit={vi.fn()} />,
    );

    expect(screen.getByTestId("document-card-metadata-author")).toHaveTextContent("Jane Smith");
    expect(screen.getByTestId("document-card-metadata-subject")).toHaveTextContent("Physics");
    // Tags list should be visible.
    const tagItems = screen.getAllByTestId("document-card-tag");
    expect(tagItems).toHaveLength(2);
    expect(tagItems[0]).toHaveTextContent("important");
  });

  it("does not render the tags list when there are no tags", () => {
    render(
      <DocumentCard document={baseDoc} onRequestDelete={vi.fn()} onRequestEdit={vi.fn()} />,
    );

    expect(screen.queryByTestId("document-card-tags")).not.toBeInTheDocument();
  });
});