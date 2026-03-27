import { SettingsPage } from "../../components/settings-page";
import { getInitialSettingsSnapshot } from "../../lib/server-api";

export default async function Page() {
  const initialSettings = await getInitialSettingsSnapshot();

  return <SettingsPage initialSettings={initialSettings} />;
}
