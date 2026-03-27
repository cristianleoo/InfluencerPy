import { ScoutsPage } from "../../components/scouts-page";
import { getInitialDashboardSnapshot } from "../../lib/server-api";

export default async function Page() {
  const initialSnapshot = await getInitialDashboardSnapshot();

  return <ScoutsPage initialSnapshot={initialSnapshot} />;
}
