"use client";

import { CourseCard } from "./CourseCard";
import type { Course } from "@/types";
import styles from "./courses.module.css";

interface CourseListProps {
  courses: readonly Course[];
  /** IDs currently in flight (edit or delete). */
  pendingIds: ReadonlySet<string>;
  onEdit: (course: Course) => void;
  onDelete: (course: Course) => void;
}

/**
 * Renders the user's courses as a responsive grid of cards. Pure
 * presentation — the parent owns the data and the request lifecycle.
 */
export function CourseList({ courses, pendingIds, onEdit, onDelete }: CourseListProps) {
  return (
    <ul className={styles.list} aria-label="Your courses" data-testid="course-list">
      {courses.map((course) => (
        <li key={course.id} className={styles.listItem} data-course-id={course.id}>
          <CourseCard
            course={course}
            pending={pendingIds.has(course.id)}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </li>
      ))}
    </ul>
  );
}
