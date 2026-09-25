import Link from "next/link";

export default function ThankYou() {
  return (
    <main className="mx-auto w-full max-w-md px-4 py-12">
      <h1 className="text-2xl font-semibold">Thank you</h1>
      <p className="mt-2 text-sm text-zinc-600">
        We received your information. You will get a confirmation email shortly, and an attorney will be in
        touch soon.
      </p>
      <Link href="/" className="mt-6 inline-block text-sm underline">
        Back to the form
      </Link>
    </main>
  );
}
