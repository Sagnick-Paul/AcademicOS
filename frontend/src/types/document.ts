import type { UUID } from "./api";

export type DocumentUploadStatus = "pending" | "uploading" | "processing" | "ready" | "failed";

export interface Document {
  id: UUID;
  owner_id: UUID;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  upload_status: DocumentUploadStatus;
  created_at: string;
  updated_at: string;
}
