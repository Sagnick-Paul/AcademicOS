// API-level envelopes + the normalized error shape used across the app.

/** UUID as a string (matches FastAPI/Pydantic). */
export type UUID = string;

export interface APIErrorPayload {
  /** Human-readable message from the backend. May be a list for 422. */
  detail: string | Array<{ loc?: Array<string | number>; msg: string; type?: string }>;
}

export class APIError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload?: APIErrorPayload,
  ) {
    super(message);
    this.name = "APIError";
  }
}

/** 204 / void response. */
export type NoContent = void;

/** Common list-pagination shape used by `?skip=&limit=` endpoints. */
export interface PageParams {
  skip?: number;
  limit?: number;
}
