"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import Field from "@/app/components/field";
import { api } from "@/lib/client";
import { errorMessage, fieldErrors, FORM_ERROR } from "@/lib/errors";

// Mirrors the server's cap so a too-big file fails before uploading. The API is the real check.
const MAX_RESUME_BYTES = 5 * 1024 * 1024;

const RESUME_ACCEPT = [
  ".pdf",
  ".doc",
  ".docx",
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
].join(",");

const FIELDS = ["first_name", "last_name", "email", "resume"] as const;

export default function LeadForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const resume = form.get("resume");

    if (resume instanceof File && resume.size > MAX_RESUME_BYTES) {
      setErrors({ resume: "File is larger than 5 MB." });
      return;
    }

    setSubmitting(true);
    setErrors({});
    const formEl = event.currentTarget;
    try {
      const { error, response } = await api.POST("/api/leads", {
        body: {
          first_name: String(form.get("first_name") ?? ""),
          last_name: String(form.get("last_name") ?? ""),
          email: String(form.get("email") ?? ""),
          // The generated type says `string` for binary fields; at runtime this is the File.
          resume: resume as unknown as string,
        },
        bodySerializer: (body) => {
          const fd = new FormData();
          for (const [key, value] of Object.entries(body)) fd.append(key, value as string | Blob);
          return fd;
        },
      });
      if (response.ok) {
        router.push("/thank-you");
        return;
      }
      if (response.status === 422 && error && "detail" in error && Array.isArray(error.detail)) {
        const next = fieldErrors(error.detail, FIELDS);
        setErrors(next);
        // Move focus to the first invalid input so keyboard and screen-reader users land on it.
        const first = FIELDS.find((f) => next[f]);
        if (first) formEl.querySelector<HTMLInputElement>(`[name="${first}"]`)?.focus();
      } else {
        setErrors({ [FORM_ERROR]: errorMessage(error, response.status) });
      }
    } catch {
      setErrors({ [FORM_ERROR]: errorMessage(null) });
    }
    // Only reached on failure; on success the button stays disabled while navigating.
    setSubmitting(false);
  }

  return (
    <form method="post" encType="multipart/form-data" onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field name="first_name" label="First name" error={errors.first_name} autoComplete="given-name" />
      <Field name="last_name" label="Last name" error={errors.last_name} autoComplete="family-name" />
      <Field name="email" label="Email" type="email" error={errors.email} autoComplete="email" />
      <Field
        name="resume"
        label="Resume"
        type="file"
        accept={RESUME_ACCEPT}
        hint="PDF, DOC or DOCX, up to 5 MB"
        error={errors.resume}
      />

      {errors[FORM_ERROR] && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {errors[FORM_ERROR]}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="mt-2 rounded-md bg-zinc-900 px-4 py-2 font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
      >
        {submitting ? "Submitting…" : "Submit"}
      </button>
    </form>
  );
}
