"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { api } from "@/lib/client";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";

import StateBadge, { STATE_LABELS } from "./state-badge";

type LeadPage = components["schemas"]["LeadPage"];
export type StateFilter = components["schemas"]["LeadState"] | undefined;

const PAGE_SIZE = 20;

const FILTERS: { label: string; state: StateFilter }[] = [
  { label: "All", state: undefined },
  { label: STATE_LABELS.PENDING, state: "PENDING" },
  { label: STATE_LABELS.REACHED_OUT, state: "REACHED_OUT" },
];

function href(state: StateFilter, offset = 0): string {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (offset > 0) params.set("offset", String(offset));
  const query = params.toString();
  return query ? `/dashboard?${query}` : "/dashboard";
}

type Result = { key: string; page?: LeadPage; error?: string };

export default function LeadList({ state, offset }: { state: StateFilter; offset: number }) {
  const key = `${state ?? ""}:${offset}`;
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    let current = true;
    api
      .GET("/api/leads", { params: { query: { state, limit: PAGE_SIZE, offset } } })
      .then(({ data, error, response }) => {
        if (!current) return;
        if (data) setResult({ key, page: data });
        // A 401 is already redirecting to /login (lib/client.ts); don't flash an error first.
        else if (response.status !== 401) setResult({ key, error: errorMessage(error, response.status) });
      })
      .catch(() => current && setResult({ key, error: errorMessage(null) }));
    return () => {
      current = false;
    };
  }, [key, state, offset]);

  // Results from a previous filter/page don't count; show loading until this one arrives.
  const shown = result?.key === key ? result : null;

  return (
    <div className="flex flex-col gap-4">
      <nav className="flex gap-2 text-sm" aria-label="Filter by state">
        {FILTERS.map((filter) => (
          <Link
            key={filter.label}
            href={href(filter.state)}
            aria-current={filter.state === state ? "page" : undefined}
            className={`rounded-md px-3 py-1 ${
              filter.state === state
                ? "bg-zinc-900 text-white"
                : "border border-zinc-300 hover:bg-zinc-100 hover:text-zinc-900"
            }`}
          >
            {filter.label}
          </Link>
        ))}
      </nav>

      {!shown && (
        <p role="status" className="text-sm text-zinc-500">
          Loading…
        </p>
      )}
      {shown?.error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {shown.error}
        </p>
      )}
      {shown?.page && <LeadTable page={shown.page} state={state} />}
    </div>
  );
}

function LeadTable({ page, state }: { page: LeadPage; state: StateFilter }) {
  if (page.items.length === 0) {
    if (page.total === 0) return <p className="text-sm text-zinc-500">No leads yet.</p>;
    // e.g. a hand-edited offset, or leads moved out of this filter while on its last page.
    return (
      <p className="text-sm text-zinc-500">
        No leads on this page.{" "}
        <Link href={href(state)} className="underline">
          Back to first page
        </Link>
      </p>
    );
  }
  const first = page.offset + 1;
  const last = page.offset + page.items.length;
  const hasPrev = page.offset > 0;
  const hasNext = last < page.total;

  return (
    <>
      <div className="overflow-x-auto rounded-md border border-zinc-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 text-zinc-500">
            <tr>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Email</th>
              <th className="px-3 py-2 font-medium">Submitted</th>
              <th className="px-3 py-2 font-medium">State</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((lead) => (
              <tr key={lead.id} className="border-b border-zinc-100 last:border-0">
                <td className="px-3 py-2">
                  <Link href={`/dashboard/leads/${lead.id}`} className="font-medium underline-offset-2 hover:underline">
                    {lead.first_name} {lead.last_name}
                  </Link>
                </td>
                <td className="px-3 py-2">{lead.email}</td>
                <td className="px-3 py-2 whitespace-nowrap">{formatDate(lead.created_at)}</td>
                <td className="px-3 py-2">
                  <StateBadge state={lead.state} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-500">
          Showing {first}–{last} of {page.total}
        </span>
        <div className="flex gap-2">
          <PageLink enabled={hasPrev} href={href(state, Math.max(0, page.offset - page.limit))}>
            Previous
          </PageLink>
          <PageLink enabled={hasNext} href={href(state, page.offset + page.limit)}>
            Next
          </PageLink>
        </div>
      </div>
    </>
  );
}

function PageLink({ enabled, href, children }: { enabled: boolean; href: string; children: string }) {
  const base = "rounded-md border border-zinc-300 px-3 py-1";
  if (!enabled) return (
      <span aria-disabled="true" className={`${base} opacity-40`}>
        {children}
      </span>
    );
  return (
    <Link href={href} className={`${base} hover:bg-zinc-100 hover:text-zinc-900`}>
      {children}
    </Link>
  );
}
