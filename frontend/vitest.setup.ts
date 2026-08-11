// Test setup: registers jest-dom matchers (toBeInTheDocument, etc.)
// and silences expected console.error output from React error boundaries
// under test (we assert these elsewhere).

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
