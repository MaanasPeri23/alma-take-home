import LeadForm from "./lead-form";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-md px-4 py-12">
      <h1 className="text-2xl font-semibold">Get in touch</h1>
      <p className="mt-2 mb-8 text-sm text-zinc-600">
        Tell us about yourself and attach your resume. An attorney will reach out.
      </p>
      <LeadForm />
    </main>
  );
}
