import { ReviewsPage } from "../../components/reviews-page";
import { getInitialDashboardSnapshot } from "../../lib/server-api";

export default async function Page() {
  const initialSnapshot = await getInitialDashboardSnapshot();

  return <ReviewsPage initialSnapshot={initialSnapshot} />;
}
