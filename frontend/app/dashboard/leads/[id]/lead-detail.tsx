"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import type { components } from "@/lib/api/schema";
import { api } from "@/lib/client";
import { errorMessage } from "@/lib/errors";
import { formatBytes, formatDate } from "@/lib/format";

import StateBadge, { STATE_LABELS } from "../../state-badge";

type LeadDetail = components["schemas"]["LeadDetail"];
type LeadState = components["schemas"]["LeadState"];

// The one action each state offers. REACHED_OUT → PENDING is the undo the API allows.
const NEXT_ACTION: Record<LeadState, { to: LeadState; label: string; primary: boolean }> = {
  PENDING: { to: "REACHED_OUT", label: "Mark as reached out", primary: true },
  REACHED_OUT: { to: "PENDING", label: "Move back to pending", primary: false },
};

type Load = { status: "loading" } | { status: "not-found" } | { status: "error"; message: string } | { status: "ok"; lead: LeadDetail };

export default function LeadDetailView({ id }: { id: string }) {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // The lead this view currently shows; late responses for another lead are dropped.
  const shownId = useRef(id);
  useEffect(() => {
    shownId.current = id;
  }, [id]);

  const fetchLead = useCallback(async (): Promise<Load | null> => {
    try {
      const { data, error, response } = await api.GET("/api/leads/{lead_id}", {
        params: { path: { lead_id: id } },
      });
      if (data) return { status: "ok", lead: data };
      // A malformed id is a 422; to the attorney it's the same as a missing lead.
      if (response.status === 404 || response.status === 422) return { status: "not-found" };
      // A 401 is already redirecting to /login (lib/client.ts); keep showing "Loading…".
      if (response.status === 401) return null;
      return { status: "error", message: errorMessage(error, response.status) };
    } catch {
      return { status: "error", message: errorMessage(null) };
    }
  }, [id]);

  useEffect(() => {
    let current = true;
    fetchLead().then((next) => {
      if (current && next) setLoad(next);
    });
    return () => {
      current = false;
    };
  }, [fetchLead]);

  async function changeState(lead: LeadDetail) {
    const action = NEXT_ACTION[lead.state];
    setSaving(true);
    setActionError(null);
    try {
      const { data, error, response } = await api.PATCH("/api/leads/{lead_id}", {
        params: { path: { lead_id: lead.id } },
        body: { state: action.to },
      });
      if (shownId.current !== lead.id) return;
      if (response.status === 401) return; // redirecting to /login; keep the button disabled
      if (data) {
        setLoad({ status: "ok", lead: data });
      } else {
        setActionError(errorMessage(error, response.status));
        // 409: someone else changed it first. Show what it is now.
        if (response.status === 409) {
          const next = await fetchLead();
          if (next && shownId.current === lead.id) setLoad(next);
        }
      }
    } catch {
      setActionError(errorMessage(null));
    }
    setSaving(false);
  }

  const back = (
    <Link href="/dashboard" className="text-sm text-zinc-500 hover:underline">
      ← All leads
    </Link>
  );

  if (load.status === "loading") {
    return (
      <p role="status" className="text-sm text-zinc-500">
        Loading…
      </p>
    );
  }
  if (load.status === "not-found") {
    return (
      <div className="flex flex-col gap-4">
        {back}
        <p>Lead not found.</p>
      </div>
    );
  }
  if (load.status === "error") {
    return (
      <div className="flex flex-col gap-4">
        {back}
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {load.message}
        </p>
      </div>
    );
  }

  const { lead } = load;
  const action = NEXT_ACTION[lead.state];
  const history = [...lead.history].reverse();

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      {back}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">
            {lead.first_name} {lead.last_name}
          </h1>
          <StateBadge state={lead.state} />
        </div>
        <button
          type="button"
          onClick={() => changeState(lead)}
          disabled={saving}
          className={`rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50 ${
            action.primary
              ? "bg-zinc-900 text-white hover:bg-zinc-700"
              : "border border-zinc-300 hover:bg-zinc-100 hover:text-zinc-900"
          }`}
        >
          {saving ? "Saving…" : action.label}
        </button>
      </div>

      {actionError && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {actionError}
        </p>
      )}

      <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-zinc-500">Email</dt>
        <dd>
          <a href={`mailto:${lead.email}`} className="underline-offset-2 hover:underline">
            {lead.email}
          </a>
        </dd>
        <dt className="text-zinc-500">Submitted</dt>
        <dd>{formatDate(lead.created_at)}</dd>
        <dt className="text-zinc-500">Resume</dt>
        <dd className="flex flex-wrap items-center gap-x-3">
          <span className="break-all">{lead.resume_filename}</span>
          <span className="text-zinc-500">{formatBytes(lead.resume_size_bytes)}</span>
          {/* A plain link, not the typed client: same-origin so the cookie is sent, and the
              API's attachment header makes it a streamed download instead of a JS blob. */}
          <a
            href={`/api/leads/${encodeURIComponent(lead.id)}/resume`}
            className="font-medium underline underline-offset-2"
          >
            Download
          </a>
        </dd>
      </dl>

      <section>
        <h2 className="mb-2 text-sm font-medium text-zinc-500">History</h2>
        {history.length === 0 ? (
          <p className="text-sm text-zinc-500">No changes yet.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm">
            {history.map((event) => (
              <li key={event.id}>
                {STATE_LABELS[event.from_state]} → {STATE_LABELS[event.to_state]} by {event.actor_name}
                <span className="text-zinc-500"> · {formatDate(event.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
