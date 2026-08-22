/**
 * Helpers that translate the frontend's three-state patch model
 * (omit / null / value) into a wire payload the backend understands.
 *
 * The backend (Pydantic v2) detects a "leave alone" instruction by
 * checking whether the key is in `model_fields_set`. Plain JSON
 * serialisation does not distinguish `undefined` from missing, so we
 * have to drop `undefined` keys explicitly before the body goes out.
 *
 * `null` survives serialisation and means "clear", which is what the
 * backend's `Optional[UUID]` / `Optional[DocumentType]` validators
 * expect.
 *
 * Anything else (a string, number, array, object) is forwarded as-is.
 */
export function stripUndefined<T extends Record<string, unknown>>(input: T): Partial<T> {
  const out: Partial<T> = {};
  for (const key of Object.keys(input) as (keyof T)[]) {
    const value = input[key];
    if (value === undefined) continue;
    out[key] = value;
  }
  return out;
}
