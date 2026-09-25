import Link from "next/link";

import AccountMenu from "./account-menu";

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-zinc-200 px-4 py-3">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <Link href="/dashboard" className="font-semibold">
            Leads
          </Link>
          <AccountMenu />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl px-4 py-8">{children}</main>
    </div>
  );
}
