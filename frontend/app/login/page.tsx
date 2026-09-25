import LoginForm from "./login-form";

// Deliberately makes no API call: with the sign-out-on-401 rule in lib/client.ts, checking
// /me here would redirect /login to itself when the cookie is stale.
export default function Login() {
  return (
    <main className="mx-auto w-full max-w-md px-4 py-12">
      <h1 className="text-2xl font-semibold">Attorney sign in</h1>
      <p className="mt-2 mb-8 text-sm text-zinc-600">Sign in to see submitted leads.</p>
      <LoginForm />
    </main>
  );
}
