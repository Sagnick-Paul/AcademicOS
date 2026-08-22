"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils/format";
import type { Course } from "@/types";
import styles from "./courses.module.css";

interface CourseCardProps {
  course: Course;
  /** True while an edit/delete request is in flight for this card. */
  pending?: boolean;
  onEdit: (course: Course) => void;
  onDelete: (course: Course) => void;
}

/**
 * Single course card. Pure presentation; the parent owns the request
 * lifecycle. The title links to the course workspace at
 * `/courses/{id}` so the user can drill in.
 */
export function CourseCard({ course, pending = false, onEdit, onDelete }: CourseCardProps) {
  return (
    <article className={styles.card} data-testid="course-card" data-course-id={course.id}>
      <header className={styles.cardHeader}>
        <div className={styles.cardTitleRow}>
          <Link
            href={`/courses/${course.id}`}
            className={styles.cardTitle}
            data-testid="course-card-title"
          >
            {course.name}
          </Link>
          {course.code ? (
            <span className={styles.cardCode} data-testid="course-card-code">
              {course.code}
            </span>
          ) : null}
        </div>
      </header>

      {course.description ? (
        <p className={styles.cardDescription} data-testid="course-card-description">
          {course.description}
        </p>
      ) : null}

      <div className={styles.cardMeta}>
        <span data-testid="course-card-updated">
          Updated {formatDate(course.updated_at)}
        </span>
      </div>

      <footer className={styles.cardActions}>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onEdit(course)}
          disabled={pending}
          data-testid="course-card-edit"
        >
          Edit
        </Button>
        <Button
          type="button"
          variant="danger"
          onClick={() => onDelete(course)}
          disabled={pending}
          data-testid="course-card-delete"
        >
          Delete
        </Button>
      </footer>
    </article>
  );
}
