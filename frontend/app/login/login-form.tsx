"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import Field from "@/app/components/field";
import { api } from "@/lib/client";
import { errorMessage, fieldErrors, FORM_ERROR } from "@/lib/errors";

const FIELDS = ["email", "password"] as const;

export default function LoginForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);

    setSubmitting(true);
    setErrors({});
    try {
      const { error, response } = await api.POST("/api/auth/login", {
        body: {
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? ""),
        },
      });
      if (response.ok) {
        router.replace("/dashboard");
        return;
      }
      if (response.status === 422 && error && "detail" in error && Array.isArray(error.detail)) {
        setErrors(fieldErrors(error.detail, FIELDS));
      } else {
        // 401 carries a user-facing detail ("Wrong email or password").
        setErrors({ [FORM_ERROR]: errorMessage(error, response.status) });
      }
    } catch {
      setErrors({ [FORM_ERROR]: errorMessage(null) });
    }
    // Only reached on failure; on success the button stays disabled while navigating.
    setSubmitting(false);
  }

  return (
    // method="post" so a submit before hydration never puts the password in the URL.
    <form method="post" onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field name="email" label="Email" type="email" error={errors.email} autoComplete="username" />
      <Field
        name="password"
        label="Password"
        type="password"
        error={errors.password}
        autoComplete="current-password"
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
        {submitting ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
