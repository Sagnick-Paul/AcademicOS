"use client";

import { useCallback, useState, type FormEvent, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/Button";
import styles from "./MessageComposer.module.css";

interface MessageComposerProps {
  /** True while a send is in flight; disables the textarea and send button. */
  pending: boolean;
  /** Optional error from the most recent send. */
  error?: string | null;
  /**
   * Optional controlled value. When provided, the composer does NOT
   * own its own input state — the parent is in charge of clearing
   * on success and restoring on error. When omitted, the composer
   * keeps its own state and clears on every submit (legacy behavior).
   */
  value?: string;
  /** Called whenever the user edits the textarea. Only relevant when `value` is provided. */
  onChange?: (next: string) => void;
  onSubmit: (text: string) => void;
}

/**
 * Multiline message composer. Enter sends, Shift+Enter inserts a
 * newline. The parent owns the request lifecycle; this component is
 * pure and never talks to the API.
 *
 * The textarea is controlled so the disabled state of the send
 * button always reflects the current value. Whitespace-only input
 * is rejected locally — the submit handler also re-checks before
 * calling the parent, so even programmatic form submission can't
 * send empty messages.
 */
export function MessageComposer({
  pending,
  error = null,
  value: controlledValue,
  onChange: controlledOnChange,
  onSubmit,
}: MessageComposerProps) {
  const [internalValue, setInternalValue] = useState("");

  // Two operating modes:
  //   - controlled (value prop provided): parent decides when to
  //     clear/restore. Used to preserve text after a failed send.
  //   - uncontrolled (no value prop): composer manages its own
  //     state and clears on submit.
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const setValue = useCallback(
    (next: string) => {
      if (isControlled) {
        controlledOnChange?.(next);
      } else {
        setInternalValue(next);
      }
    },
    [isControlled, controlledOnChange],
  );

  const isEmpty = value.trim().length === 0;
  const disabled = pending || isEmpty;

  const submit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || pending) return;
    onSubmit(trimmed);
    if (!isControlled) {
      setInternalValue("");
    }
    // In controlled mode, the parent decides when to clear (or
    // restore the text on error). The composer intentionally does
    // not clear here.
  }, [value, pending, onSubmit, isControlled]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      className={styles.root}
      onSubmit={handleSubmit}
      aria-label="Message composer"
      data-testid="chat-composer"
    >
      {error ? (
        <div className={styles.error} role="alert" data-testid="chat-composer-error">
          {error}
        </div>
      ) : null}
      <div className={styles.row}>
        <label htmlFor="chat-composer-input" className={styles.srOnly}>
          Ask a question
        </label>
        <textarea
          id="chat-composer-input"
          className={styles.input}
          rows={1}
          placeholder={
            pending ? "Generating response…" : "Ask a question about your documents…"
          }
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={pending}
          data-testid="chat-composer-input"
          aria-label="Message"
        />
        <Button
          type="submit"
          variant="primary"
          disabled={disabled}
          data-testid="chat-composer-send"
        >
          {pending ? "Sending…" : "Send"}
        </Button>
      </div>
      <div className={styles.hint}>
        Press <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for newline
      </div>
    </form>
  );
}
