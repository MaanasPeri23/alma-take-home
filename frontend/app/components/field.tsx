// Labelled input with an optional hint and an error message wired up for screen readers.
type FieldProps = {
  name: string;
  label: string;
  error?: string;
  hint?: string;
  type?: string;
  accept?: string;
  autoComplete?: string;
};

export default function Field({ name, label, error, hint, type = "text", accept, autoComplete }: FieldProps) {
  const id = `field-${name}`;
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ");
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        accept={accept}
        autoComplete={autoComplete}
        required
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className={`rounded-md border px-3 py-2 text-sm ${
          error ? "border-red-500" : "border-zinc-300"
        } file:mr-3 file:rounded file:border-0 file:bg-zinc-200 file:text-zinc-900 file:px-2 file:py-1`}
      />
      {hint && (
        <p id={`${id}-hint`} className="text-xs text-zinc-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
