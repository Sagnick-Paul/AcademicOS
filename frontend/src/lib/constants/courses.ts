/**
 * Constants and pure helpers for the Course domain.
 *
 * Centralised so the sidebar, list panel, and form components agree on
 * the same labels and limits. The backend's source of truth lives in
 * `backend/app/schemas/course.py` — keep the limits in sync.
 */

export const COURSE_NAME_MAX = 255;
export const COURSE_CODE_MAX = 64;
export const COURSE_DESCRIPTION_MAX = 2000;

export interface CourseValidationErrors {
  name?: string;
  code?: string;
  description?: string;
}

/**
 * Validate a `CourseCreate` / `CourseUpdate` payload before it leaves
 * the browser. Mirrors the backend's Pydantic constraints so users see
 * errors immediately, but the backend remains the source of truth.
 */
export function validateCourse(input: {
  name?: string | null;
  code?: string | null;
  description?: string | null;
}): CourseValidationErrors {
  const errors: CourseValidationErrors = {};

  if (input.name !== undefined && input.name !== null) {
    const trimmed = input.name.trim();
    if (!trimmed) {
      errors.name = "Course name is required.";
    } else if (trimmed.length > COURSE_NAME_MAX) {
      errors.name = `Course name must be ${COURSE_NAME_MAX} characters or fewer.`;
    }
  }

  if (input.code !== undefined && input.code !== null && input.code !== "") {
    const trimmed = input.code.trim();
    if (!trimmed) {
      errors.code = "Course code must not be only whitespace.";
    } else if (trimmed.length > COURSE_CODE_MAX) {
      errors.code = `Course code must be ${COURSE_CODE_MAX} characters or fewer.`;
    }
  }

  if (input.description !== undefined && input.description !== null && input.description !== "") {
    const trimmed = input.description.trim();
    if (!trimmed) {
      errors.description = "Description must not be only whitespace.";
    } else if (trimmed.length > COURSE_DESCRIPTION_MAX) {
      errors.description = `Description must be ${COURSE_DESCRIPTION_MAX} characters or fewer.`;
    }
  }

  return errors;
}

export function hasCourseErrors(errors: CourseValidationErrors): boolean {
  return Boolean(errors.name || errors.code || errors.description);
}
