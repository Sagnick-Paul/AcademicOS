import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DeleteConfirmDialog } from "../DeleteConfirmDialog";

describe("DeleteConfirmDialog", () => {
  it("renders the document name and calls onConfirm when Delete is clicked", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <DeleteConfirmDialog
        documentName="lecture-1.pdf"
        pending={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByTestId("delete-confirm-dialog")).toHaveTextContent("lecture-1.pdf");
    expect(screen.getByTestId("delete-confirm-dialog")).toHaveAttribute("role", "alertdialog");

    await userEvent.click(screen.getByTestId("delete-confirm-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when Cancel is clicked", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <DeleteConfirmDialog
        documentName="lecture-1.pdf"
        pending={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    await userEvent.click(screen.getByTestId("delete-confirm-cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("disables both buttons while pending is true", () => {
    render(
      <DeleteConfirmDialog
        documentName="lecture-1.pdf"
        pending
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("delete-confirm-confirm")).toBeDisabled();
    expect(screen.getByTestId("delete-confirm-confirm")).toHaveTextContent(/deleting/i);
    expect(screen.getByTestId("delete-confirm-cancel")).toBeDisabled();
  });

  it("closes on Escape when not pending", async () => {
    const onCancel = vi.fn();
    render(
      <DeleteConfirmDialog
        documentName="lecture-1.pdf"
        pending={false}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );

    await userEvent.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("does not close on Escape when pending", async () => {
    const onCancel = vi.fn();
    render(
      <DeleteConfirmDialog
        documentName="lecture-1.pdf"
        pending
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );

    await userEvent.keyboard("{Escape}");
    expect(onCancel).not.toHaveBeenCalled();
  });
});