import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DocumentDetailPanel } from "../DocumentDetailPanel";
import { documentsApi } from "@/lib/api/documents";
import { coursesApi } from "@/lib/api/courses";
import type { Document } from "@/types";

const mockRouter = {
  push: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/documents/doc-123",
}));

vi.mock("@/lib/api/documents", () => ({
  documentsApi: {
    get: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

vi.mock("@/lib/api/courses", () => ({
  coursesApi: {
    list: vi.fn(),
  },
}));

const mockDoc: Document = {
  id: "doc-123",
  owner_id: "user-1",
  filename: "test.pdf",
  original_filename: "test.pdf",
  file_type: "pdf",
  file_size: 1024,
  storage_path: "path/test.pdf",
  upload_status: "ready",
  course_id: "course-1",
  document_type: "lecture_notes",
  document_metadata: {
    author: "Test Author",
    subject: "Test Subject",
    semester: "5",
    academic_year: "2026-27",
    tags: ["test", "pdf"],
  },
  created_at: "2026-08-20T10:00:00Z",
  updated_at: "2026-08-20T10:00:00Z",
};

describe("DocumentDetailPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a loading state initially", () => {
    vi.mocked(documentsApi.get).mockImplementation(() => new Promise(() => {}));
    vi.mocked(coursesApi.list).mockImplementation(() => new Promise(() => {}));
    
    render(<DocumentDetailPanel documentId="doc-123" />);
    
    expect(screen.getByTestId("document-detail-loading")).toBeInTheDocument();
  });

  it("renders the document details on successful load", async () => {
    vi.mocked(documentsApi.get).mockResolvedValue(mockDoc);
    vi.mocked(coursesApi.list).mockResolvedValue({
      items: [{ id: "course-1", name: "Test Course", code: "CS101", owner_id: "user-1", description: "test desc", created_at: "", updated_at: "" }]
    });
    
    render(<DocumentDetailPanel documentId="doc-123" />);
    
    await waitFor(() => {
      expect(screen.getByTestId("document-detail-ready")).toBeInTheDocument();
    });

    expect(screen.getAllByText("test.pdf")).toHaveLength(2);
    expect(screen.getAllByText(/Lecture Notes/)[0]).toBeInTheDocument();
    expect(screen.getByText(/CS101 — Test Course/)).toBeInTheDocument();
    
    // Metadata
    expect(screen.getByText("Test Author")).toBeInTheDocument();
    expect(screen.getByText("Test Subject")).toBeInTheDocument();
    
    // Tags
    expect(screen.getByText("test")).toBeInTheDocument();
    expect(screen.getByText("pdf")).toBeInTheDocument();
  });

  it("renders an empty state gracefully for missing metadata and course", async () => {
    vi.mocked(documentsApi.get).mockResolvedValue({
      ...mockDoc,
      course_id: null,
      document_type: null,
      document_metadata: null,
    });
    vi.mocked(coursesApi.list).mockResolvedValue({ items: [] });
    
    render(<DocumentDetailPanel documentId="doc-123" />);
    
    await waitFor(() => {
      expect(screen.getByTestId("document-detail-ready")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Unassigned")[0]).toBeInTheDocument(); // Header and info
    expect(screen.getAllByText("Untyped")[0]).toBeInTheDocument();
    
    expect(screen.getAllByText("Not specified")).toHaveLength(4); // Author, Subject, Semester, Year
    expect(screen.getByText("No tags")).toBeInTheDocument();
  });

  it("opens the edit dialog when Edit is clicked and handles update", async () => {
    const user = userEvent.setup();
    vi.mocked(documentsApi.get).mockResolvedValue(mockDoc);
    vi.mocked(coursesApi.list).mockResolvedValue({ items: [] });
    vi.mocked(documentsApi.update).mockResolvedValue({ ...mockDoc, original_filename: "updated.pdf" });
    
    render(<DocumentDetailPanel documentId="doc-123" />);
    
    await waitFor(() => {
      expect(screen.getByTestId("document-detail-ready")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Edit Document" }));
    
    const dialog = screen.getByTestId("document-edit-dialog");
    expect(dialog).toBeInTheDocument();
    
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    
    await waitFor(() => {
      expect(documentsApi.update).toHaveBeenCalledWith("doc-123", expect.any(Object));
      // Ensure the dialog closes
      expect(screen.queryByTestId("document-edit-dialog")).not.toBeInTheDocument();
    });
  });

  it("opens the delete dialog and navigates away on deletion", async () => {
    const user = userEvent.setup();
    vi.mocked(documentsApi.get).mockResolvedValue(mockDoc);
    vi.mocked(coursesApi.list).mockResolvedValue({ items: [] });
    vi.mocked(documentsApi.remove).mockResolvedValue(undefined);
    
    render(<DocumentDetailPanel documentId="doc-123" />);
    
    await waitFor(() => {
      expect(screen.getByTestId("document-detail-ready")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Delete Document" }));
    
    const dialog = screen.getByTestId("delete-confirm-dialog");
    expect(dialog).toBeInTheDocument();
    
    await user.click(screen.getByRole("button", { name: "Delete" }));
    
    await waitFor(() => {
      expect(documentsApi.remove).toHaveBeenCalledWith("doc-123");
      expect(mockRouter.push).toHaveBeenCalledWith("/documents");
    });
  });
});
