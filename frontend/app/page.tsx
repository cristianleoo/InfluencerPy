import { OverviewPage } from "../components/overview-page";
import { getInitialDashboardSnapshot } from "../lib/server-api";

export default async function Page() {
  const initialSnapshot = await getInitialDashboardSnapshot();

  return <OverviewPage initialSnapshot={initialSnapshot} />;
}
