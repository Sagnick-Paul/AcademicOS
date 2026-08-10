import styles from "./ErrorState.module.css";

interface Props {
  title?: string;
  description?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "Please try again in a moment.",
}: Props) {
  return (
    <div role="alert" className={styles.root}>
      <div className={styles.title}>{title}</div>
      <div className={styles.description}>{description}</div>
    </div>
  );
}
