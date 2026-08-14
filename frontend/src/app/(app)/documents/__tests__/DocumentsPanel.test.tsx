import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const {
  mockDocumentsApi,
} = vi.hoisted(() => ({
  mockDocumentsApi: {
    list: vi.fn(),
    upload: vi.fn(),
    get: vi.fn(),
    remove: vi.fn(),
  },
}));
vi.mock("@/lib/api/documents", () => ({ documentsApi: mockDocumentsApi }));

import { DocumentsPanel } from "../DocumentsPanel";
import { renderWithAuth } from "@/test-utils/wrappers";
import { APIError } from "@/types/api";
import type { Document } from "@/types";

const fakePdf: Document = {
  id: "00000000-0000-0000-0000-000000000001",
  owner_id: "00000000-0000-0000-0000-000000000099",
  filename: "abc123.pdf",
  original_filename: "lecture-1.pdf",
  file_type: "pdf",
  file_size: 1024 * 1024 * 1.4,
  storage_path: "pdf/abc123.pdf",
  upload_status: "ready",
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

const fakeProcessing: Document = {
  id: "00000000-0000-0000-0000-000000000002",
  owner_id: "00000000-0000-0000-0000-000000000099",
  filename: "abc456.png",
  original_filename: "diagram.png",
  file_type: "png",
  file_size: 2048,
  storage_path: "images/abc456.png",
  upload_status: "processing",
  created_at: "2026-01-02T08:30:00Z",
  updated_at: "2026-01-02T08:30:00Z",
};

const fakeFailed: Document = {
  id: "00000000-0000-0000-0000-000000000003",
  owner_id: "00000000-0000-0000-0000-000000000099",
  filename: "abc789.pptx",
  original_filename: "broken.pptx",
  file_type: "pptx",
  file_size: 4096,
  storage_path: "ppt/abc789.pptx",
  upload_status: "failed",
  created_at: "2026-01-03T10:00:00Z",
  updated_at: "2026-01-03T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

function makeFile(name: string, type: string, sizeBytes = 10): File {
  // jsdom's File supports a third size argument in modern versions.
  return new File([new Uint8Array(sizeBytes)], name, { type });
}

describe("DocumentsPanel", () => {
  describe("loading", () => {
    it("renders a loading state while documents are being fetched", () => {
      mockDocumentsApi.list.mockReturnValue(new Promise(() => {})); // never resolves

      renderWithAuth(<DocumentsPanel />);

      expect(screen.getByTestId("documents-loading")).toBeInTheDocument();
    });
  });

  describe("successful fetch", () => {
    it("renders documents returned by the backend", async () => {
      mockDocumentsApi.list.mockResolvedValue([fakePdf, fakeProcessing, fakeFailed]);

      renderWithAuth(<DocumentsPanel />);

      const list = await screen.findByTestId("document-list");
      const items = within(list).getAllByTestId("document-card");
      expect(items).toHaveLength(3);

      // First card renders the filename, type, size, and status.
      const firstCard = items[0];
      expect(within(firstCard).getByText("lecture-1.pdf")).toBeInTheDocument();
      expect(within(firstCard).getByTestId("document-card-type")).toHaveTextContent("PDF");
      expect(within(firstCard).getByTestId("document-card-status")).toHaveTextContent("Ready");

      // Processing and Failed statuses render distinctly.
      expect(within(items[1]).getByTestId("document-card-status")).toHaveTextContent("Processing");
      expect(within(items[2]).getByTestId("document-card-status")).toHaveTextContent("Failed");
    });

    it("does not invent documents when the API returns an empty list", async () => {
      mockDocumentsApi.list.mockResolvedValue([]);

      renderWithAuth(<DocumentsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId("documents-empty-state")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("document-list")).not.toBeInTheDocument();
    });
  });

  describe("error", () => {
    it("renders an error state when the list request fails", async () => {
      mockDocumentsApi.list.mockRejectedValue(new APIError("Network error", 500));

      renderWithAuth(<DocumentsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(/network error/i);
      });
      expect(screen.queryByTestId("documents-loading")).not.toBeInTheDocument();
      expect(screen.queryByTestId("document-list")).not.toBeInTheDocument();
    });

    it("calls refresh when the refresh button is clicked", async () => {
      mockDocumentsApi.list.mockResolvedValueOnce([]).mockResolvedValueOnce([fakePdf]);

      renderWithAuth(<DocumentsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId("documents-empty-state")).toBeInTheDocument();
      });

      await userEvent.click(screen.getByTestId("documents-refresh"));

      await waitFor(() => {
        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });
      expect(mockDocumentsApi.list).toHaveBeenCalledTimes(2);
    });
  });

  describe("upload", () => {
    it("uploads the selected file and refreshes the list on success", async () => {
      mockDocumentsApi.list
        .mockResolvedValueOnce([]) // initial
        .mockResolvedValueOnce([fakePdf]); // after upload
      mockDocumentsApi.upload.mockResolvedValue(fakePdf);

      renderWithAuth(<DocumentsPanel />);

      // Wait for the empty state.
      await screen.findByTestId("documents-empty-state");

      const input = screen.getByTestId("document-upload-input") as HTMLInputElement;
      const file = makeFile("lecture.pdf", "application/pdf", 1024);
      await userEvent.upload(input, file);

      expect(mockDocumentsApi.upload).toHaveBeenCalledTimes(1);
      // documentsApi.upload wraps the File in a FormData internally —
      // the spy sees the raw `File` we passed to the API method.
      const passedFile = mockDocumentsApi.upload.mock.calls[0][0] as File;
      expect(passedFile).toBeInstanceOf(File);
      expect(passedFile.name).toBe("lecture.pdf");

      // List refreshes — the new doc shows up.
      await waitFor(() => {
        expect(screen.getByTestId("document-list")).toBeInTheDocument();
      });
      expect(screen.getByText("lecture-1.pdf")).toBeInTheDocument();
    });

    it("disables the upload controls while a request is in flight", async () => {
      let resolveUpload: (value: Document) => void = () => undefined;
      mockDocumentsApi.upload.mockReturnValue(new Promise<Document>((res) => { resolveUpload = res; }));
      mockDocumentsApi.list.mockResolvedValue([fakePdf]);

      renderWithAuth(<DocumentsPanel />);
      await screen.findByTestId("document-list");

      const input = screen.getByTestId("document-upload-input") as HTMLInputElement;
      await userEvent.upload(input, makeFile("notes.pdf", "application/pdf"));

      await waitFor(() => {
        expect(screen.getByTestId("document-upload-button")).toBeDisabled();
      });
      expect(input).toBeDisabled();

      // Finish the upload.
      resolveUpload(fakePdf);
      await waitFor(() => {
        expect(screen.getByTestId("document-upload-button")).not.toBeDisabled();
      });
    });

    it("surfaces the backend error message when upload fails", async () => {
      mockDocumentsApi.list.mockResolvedValue([]);
      mockDocumentsApi.upload.mockRejectedValue(
        new APIError("Unsupported file type: detection", 415),
      );

      renderWithAuth(<DocumentsPanel />);
      await screen.findByTestId("documents-empty-state");

      await userEvent.upload(
        screen.getByTestId("document-upload-input") as HTMLInputElement,
        makeFile("lecture.pdf", "application/pdf"),
      );

      await waitFor(() => {
        expect(screen.getByTestId("document-upload-hint")).toHaveTextContent(
          /unsupported file type/i,
        );
      });
    });
  });

  describe("delete", () => {
    it("opens the confirmation dialog when Delete is clicked and removes the doc after confirm", async () => {
      mockDocumentsApi.list
        .mockResolvedValueOnce([fakePdf]) // initial
        .mockResolvedValueOnce([]); // after delete
      mockDocumentsApi.remove.mockResolvedValue(undefined);

      renderWithAuth(<DocumentsPanel />);

      const card = await screen.findByTestId("document-card");
      await userEvent.click(within(card).getByTestId("document-card-delete"));

      // Dialog appears.
      expect(screen.getByTestId("delete-confirm-dialog")).toBeInTheDocument();
      expect(screen.getByTestId("delete-confirm-dialog")).toHaveTextContent("lecture-1.pdf");

      await userEvent.click(screen.getByTestId("delete-confirm-confirm"));

      await waitFor(() => {
        expect(mockDocumentsApi.remove).toHaveBeenCalledWith(fakePdf.id);
      });

      // Dialog closes, list refreshes to empty.
      await waitFor(() => {
        expect(screen.queryByTestId("delete-confirm-dialog")).not.toBeInTheDocument();
      });
      expect(screen.getByTestId("documents-empty-state")).toBeInTheDocument();
    });

    it("does not call the API when the user cancels the dialog", async () => {
      mockDocumentsApi.list.mockResolvedValue([fakePdf]);

      renderWithAuth(<DocumentsPanel />);

      const card = await screen.findByTestId("document-card");
      await userEvent.click(within(card).getByTestId("document-card-delete"));

      await userEvent.click(screen.getByTestId("delete-confirm-cancel"));

      expect(mockDocumentsApi.remove).not.toHaveBeenCalled();
      expect(screen.queryByTestId("delete-confirm-dialog")).not.toBeInTheDocument();
      expect(screen.getByTestId("document-list")).toBeInTheDocument();
    });

    it("surfaces the backend error and keeps the dialog open when delete fails", async () => {
      mockDocumentsApi.list.mockResolvedValue([fakePdf]);
      mockDocumentsApi.remove.mockRejectedValue(new APIError("Document not found", 404));

      renderWithAuth(<DocumentsPanel />);

      const card = await screen.findByTestId("document-card");
      await userEvent.click(within(card).getByTestId("document-card-delete"));

      await userEvent.click(screen.getByTestId("delete-confirm-confirm"));

      await waitFor(() => {
        expect(screen.getByTestId("documents-delete-error")).toHaveTextContent(
          /document not found/i,
        );
      });

      // Dialog stays open so the user can retry or cancel.
      expect(screen.getByTestId("delete-confirm-dialog")).toBeInTheDocument();
      // Card still present (no optimistic removal).
      expect(screen.getByTestId("document-card")).toBeInTheDocument();
    });
  });

  describe("authentication", () => {
    it("attaches the bearer token on every API call", async () => {
      mockDocumentsApi.list.mockResolvedValue([]);

      renderWithAuth(<DocumentsPanel />, {
        accessToken: "test-token",
        status: "authenticated",
        user: {
          id: "u1",
          full_name: "Jane Doe",
          email: "jane@example.com",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      });

      await screen.findByTestId("documents-empty-state");
      expect(mockDocumentsApi.list).toHaveBeenCalled();
    });

    it("treats 401 errors as user-visible failures without crashing", async () => {
      mockDocumentsApi.list.mockRejectedValue(new APIError("Not authenticated", 401));

      renderWithAuth(<DocumentsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(/not authenticated/i);
      });
    });
  });

  describe("accessibility", () => {
    it("renders the page heading and subtitle with the correct text", () => {
      mockDocumentsApi.list.mockReturnValue(new Promise(() => {}));

      renderWithAuth(<DocumentsPanel />);

      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/^Documents$/);
      expect(screen.getByText(/your academic knowledge base/i)).toBeInTheDocument();
    });
  });
});