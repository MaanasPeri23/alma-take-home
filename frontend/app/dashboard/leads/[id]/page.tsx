import LeadDetailView from "./lead-detail";

export default async function LeadPage({ params }: PageProps<"/dashboard/leads/[id]">) {
  const { id } = await params;
  return <LeadDetailView id={id} />;
}
