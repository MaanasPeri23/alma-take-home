import LeadList, { type StateFilter } from "./lead-list";

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

// Filter and page live in the URL so reload and back work. Anything unexpected falls back to
// "all leads, first page"; the API validates again anyway.
export default async function Dashboard({ searchParams }: PageProps<"/dashboard">) {
  const query = await searchParams;
  const rawState = one(query.state);
  const state: StateFilter =
    rawState === "PENDING" || rawState === "REACHED_OUT" ? rawState : undefined;
  const rawOffset = Number(one(query.offset));
  const offset = Number.isSafeInteger(rawOffset) && rawOffset > 0 ? rawOffset : 0;

  return <LeadList state={state} offset={offset} />;
}
