import type { ReactNode } from "react";
import styles from "./PageContainer.module.css";

interface Props {
  children: ReactNode;
}

export function PageContainer({ children }: Props) {
  return <div className={styles.container}>{children}</div>;
}
