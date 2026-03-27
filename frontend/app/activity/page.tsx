import { ActivityPage } from "../../components/activity-page";
import { getInitialDashboardSnapshot } from "../../lib/server-api";

export default async function Page() {
  const initialSnapshot = await getInitialDashboardSnapshot();

  return <ActivityPage initialSnapshot={initialSnapshot} />;
}
