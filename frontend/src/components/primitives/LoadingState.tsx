import styles from "./LoadingState.module.css";

interface Props {
  label?: string;
}

export function LoadingState({ label = "Loading…" }: Props) {
  return (
    <div role="status" aria-live="polite" className={styles.root}>
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
    </div>
  );
}
