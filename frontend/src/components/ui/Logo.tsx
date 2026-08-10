import styles from "./Logo.module.css";

interface Props {
  size?: "sm" | "md";
  showWordmark?: boolean;
}

export function Logo({ size = "md", showWordmark = true }: Props) {
  const dim = size === "sm" ? 22 : 28;
  return (
    <span className={styles.logo} data-testid="logo">
      <span className={styles.mark} style={{ width: dim, height: dim }}>
        AO
      </span>
      {showWordmark && <span className={styles.wordmark}>AcademicOS</span>}
    </span>
  );
}
