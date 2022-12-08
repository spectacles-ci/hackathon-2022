import type { LoaderArgs } from "@remix-run/node";
import { AbandonedDashboardResult } from "../../models";
import { getSession } from "~/sessions";
import { fetchStats, getCredentials } from "~/utils";

export const loader = async ({ request }: LoaderArgs) => {
  const session = await getSession(request.headers.get("Cookie"));
  const credentialId = session.get("credentialId");
  const { baseUrl, clientId, clientSecret } = await getCredentials(
    credentialId
  );
  return await fetchStats<AbandonedDashboardResult>(
    "/stats/abandoned_dashboards",
    baseUrl,
    clientId,
    clientSecret
  );
};
