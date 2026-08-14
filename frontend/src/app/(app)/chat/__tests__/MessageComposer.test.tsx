import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MessageComposer } from "../components/MessageComposer";

describe("MessageComposer", () => {
  it("renders the textarea and send button", () => {
    render(<MessageComposer pending={false} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("chat-composer-input")).toBeInTheDocument();
    expect(screen.getByTestId("chat-composer-send")).toBeInTheDocument();
  });

  it("disables the send button when the textarea is empty", () => {
    render(<MessageComposer pending={false} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
  });

  it("disables the send button when the textarea contains only whitespace", async () => {
    const user = userEvent.setup();
    render(<MessageComposer pending={false} onSubmit={vi.fn()} />);
    const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
    await user.type(input, "   ");
    expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
  });

  it("enables the send button when the user types content", async () => {
    const user = userEvent.setup();
    render(<MessageComposer pending={false} onSubmit={vi.fn()} />);
    const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
    await user.type(input, "Hello");
    expect(screen.getByTestId("chat-composer-send")).toBeEnabled();
  });

  it("invokes onSubmit with the trimmed text and clears the input on submit", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MessageComposer pending={false} onSubmit={onSubmit} />);
    const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
    await user.type(input, "  Explain transformers  ");
    await user.click(screen.getByTestId("chat-composer-send"));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("Explain transformers");
    expect(input.value).toBe("");
  });

  it("sends on Enter but inserts a newline on Shift+Enter", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MessageComposer pending={false} onSubmit={onSubmit} />);
    const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
    await user.type(input, "Hi");
    await user.keyboard("{Enter}");
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(input.value).toBe("");

    // After the first send, typing + Shift+Enter should add a
    // newline, NOT send again.
    await user.type(input, "Line 1");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(input, "Line 2");
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(input.value).toBe("Line 1\nLine 2");
  });

  it("prevents sending an empty message via form submission", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MessageComposer pending={false} onSubmit={onSubmit} />);
    // Even though the button is disabled, try submitting the form
    // directly to confirm the handler short-circuits.
    const form = screen.getByTestId("chat-composer");
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables both textarea and send button while pending", () => {
    render(<MessageComposer pending={true} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("chat-composer-input")).toBeDisabled();
    expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
  });

  it("renders an inline error when one is provided", () => {
    render(<MessageComposer pending={false} error="Service unavailable" onSubmit={vi.fn()} />);
    const error = screen.getByTestId("chat-composer-error");
    expect(error).toHaveTextContent(/service unavailable/i);
    expect(error).toHaveAttribute("role", "alert");
  });

  it("prevents sending while pending (no duplicate submissions)", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MessageComposer pending={true} onSubmit={onSubmit} />);
    const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
    expect(input).toBeDisabled();
    // Force the change event to confirm submit() short-circuits.
    input.value = "ignored";
    await user.click(screen.getByTestId("chat-composer-send"));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
