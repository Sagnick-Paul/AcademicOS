"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { coursesApi } from "@/lib/api/courses";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { Button } from "@/components/ui/Button";
import { APIError } from "@/types/api";
import type { Course, CourseCreate, CourseUpdate } from "@/types";
import { CourseDeleteDialog } from "./CourseDeleteDialog";
import { CourseForm } from "./CourseForm";
import { CourseList } from "./CourseList";
import styles from "./courses.module.css";

type ListState =
  | { status: "loading" }
  | { status: "ready"; courses: Course[] }
  | { status: "error"; message: string };

/** The form is either closed, creating a new course, or editing one. */
type FormMode =
  | { mode: "closed" }
  | { mode: "create" }
  | { mode: "edit"; course: Course };

/**
 * /courses — list + create + edit + delete. Mirrors the lifecycle
 * ownership pattern from `DocumentsPanel`: this component owns every
 * async request, the children are pure presentational.
 */
export function CoursesPanel() {
  const router = useRouter();
  const [list, setList] = useState<ListState>({ status: "loading" });
  const [form, setForm] = useState<FormMode>({ mode: "closed" });
  const [pendingDelete, setPendingDelete] = useState<Course | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [updatePending, setUpdatePending] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  // ---------- load ----------

  const refresh = useCallback(async () => {
    setList({ status: "loading" });
    try {
      const response = await coursesApi.list();
      setList({ status: "ready", courses: response.items });
    } catch (err) {
      setList({
        status: "error",
        message:
          err instanceof APIError ? err.message : "Could not load courses",
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await coursesApi.list();
        if (cancelled) return;
        setList({ status: "ready", courses: response.items });
      } catch (err) {
        if (cancelled) return;
        setList({
          status: "error",
          message:
            err instanceof APIError
              ? err.message
              : "Could not load courses",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // ---------- create / update ----------

  const handleCreate = useCallback(
    async (payload: CourseCreate | CourseUpdate) => {
      setCreatePending(true);
      setCreateError(null);
      try {
        await coursesApi.create(payload as CourseCreate);
        const response = await coursesApi.list();
        setList({ status: "ready", courses: response.items });
        setForm({ mode: "closed" });
      } catch (err) {
        setCreateError(
          err instanceof APIError
            ? err.message
            : "Could not create the course. Please try again.",
        );
      } finally {
        setCreatePending(false);
      }
    },
    [],
  );

  const handleUpdate = useCallback(
    async (courseId: string, payload: CourseUpdate) => {
      setUpdatePending(true);
      setUpdateError(null);
      try {
        await coursesApi.update(courseId, payload);
        const response = await coursesApi.list();
        setList({ status: "ready", courses: response.items });
        setForm({ mode: "closed" });
      } catch (err) {
        setUpdateError(
          err instanceof APIError
            ? err.message
            : "Could not update the course. Please try again.",
        );
      } finally {
        setUpdatePending(false);
      }
    },
    [],
  );

  // ---------- delete ----------

  const handleRequestDelete = useCallback((course: Course) => {
    setDeleteError(null);
    setPendingDelete(course);
  }, []);

  const handleCancelDelete = useCallback(() => {
    if (deletingId) return;
    setPendingDelete(null);
    setDeleteError(null);
  }, [deletingId]);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    setDeletingId(pendingDelete.id);
    setDeleteError(null);
    try {
      await coursesApi.remove(pendingDelete.id);
      setPendingDelete(null);
      const response = await coursesApi.list();
      setList({ status: "ready", courses: response.items });
    } catch (err) {
      setDeleteError(
        err instanceof APIError
          ? err.message
          : "Delete failed. Please try again.",
      );
    } finally {
      setDeletingId(null);
    }
  }, [pendingDelete]);

  // ---------- render ----------

  const renderListContent = () => {
    if (list.status === "loading") {
      return (
        <div className={styles.loadingPanel} data-testid="courses-loading">
          <LoadingState label="Loading courses…" />
        </div>
      );
    }

    if (list.status === "error") {
      return (
        <ErrorState
          title="Could not load courses"
          description={list.message}
        />
      );
    }

    if (list.courses.length === 0) {
      return (
        <div data-testid="courses-empty-state">
          <EmptyState
            title="No courses yet"
            description="Create your first course to organise related documents and conversations."
          />
        </div>
      );
    }

    const pending = new Set<string>();
    if (deletingId) pending.add(deletingId);

    return (
      <CourseList
        courses={list.courses}
        pendingIds={pending}
        onEdit={(course) => {
          setForm({ mode: "edit", course });
          setUpdateError(null);
        }}
        onDelete={handleRequestDelete}
      />
    );
  };

  const canRefresh = list.status !== "loading";

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerText}>
          <h1 className={styles.title}>Courses</h1>
          <p className={styles.subtitle}>
            Group documents and conversations by course.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button
            type="button"
            variant="ghost"
            onClick={() => void refresh()}
            disabled={!canRefresh}
            data-testid="courses-refresh"
          >
            {list.status === "loading" ? "Refreshing…" : "Refresh"}
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={() => {
              setForm({ mode: "create" });
              setCreateError(null);
            }}
            disabled={form.mode === "create"}
            data-testid="courses-new"
          >
            New course
          </Button>
        </div>
      </header>

      {form.mode === "create" ? (
        <section className={styles.createSection} aria-label="Create course">
          <CourseForm
            pending={createPending}
            errorMessage={createError}
            onSubmit={(payload) => void handleCreate(payload)}
            onCancel={() => {
              setForm({ mode: "closed" });
              setCreateError(null);
            }}
            submitLabel="Create course"
          />
        </section>
      ) : null}

      {form.mode === "edit" ? (
        <section className={styles.createSection} aria-label="Edit course">
          <CourseForm
            key={form.course.id}
            course={form.course}
            pending={updatePending}
            errorMessage={updateError}
            onSubmit={(payload) => void handleUpdate(form.course.id, payload)}
            onCancel={() => {
              setForm({ mode: "closed" });
              setUpdateError(null);
            }}
            submitLabel="Save changes"
          />
        </section>
      ) : null}

      <section className={styles.listSection} aria-label="Your courses">
        {renderListContent()}
        {deleteError ? (
          <div className={styles.deleteError} role="alert" data-testid="courses-delete-error">
            {deleteError}
          </div>
        ) : null}
      </section>

      {pendingDelete ? (
        <CourseDeleteDialog
          courseName={pendingDelete.name}
          pending={deletingId !== null}
          onCancel={handleCancelDelete}
          onConfirm={() => void handleConfirmDelete()}
        />
      ) : null}

      {/* Hidden helper used by the integration test that follows the
          "create → edit → delete" lifecycle through the router. */}
      <button
        type="button"
        hidden
        onClick={() => router.push("/dashboard")}
        data-testid="courses-router-stub"
      />
    </div>
  );
}
