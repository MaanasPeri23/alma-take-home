import type { components } from "@/lib/api/schema";

type ValidationError = components["schemas"]["ValidationError"];

// Key for errors that don't belong to a single input.
export const FORM_ERROR = "_form";

// Maps FastAPI's 422 detail list to one message per field. The field is the last string in
// `loc`, so ["body", "resume"] → "resume". Anything not in `fields` goes under FORM_ERROR so it
// is still shown somewhere.
export function fieldErrors(
  detail: ValidationError[] | undefined,
  fields: readonly string[],
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const item of detail ?? []) {
    const field = [...item.loc].reverse().find((part) => typeof part === "string");
    const key = typeof field === "string" && fields.includes(field) ? field : FORM_ERROR;
    errors[key] ??= item.msg;
  }
  return errors;
}

// Message for a non-422 failure. 4xx {"detail": "..."} strings (401/404/409) are written for
// users; 5xx details are server internals, so those get a generic message with the status.
export function errorMessage(error: unknown, status?: number): string {
  if (
    status !== undefined &&
    status < 500 &&
    error &&
    typeof error === "object" &&
    "detail" in error &&
    typeof error.detail === "string"
  ) {
    return error.detail;
  }
  const code = status ? ` (HTTP ${status})` : "";
  return `Something went wrong${code}. Please try again.`;
}
