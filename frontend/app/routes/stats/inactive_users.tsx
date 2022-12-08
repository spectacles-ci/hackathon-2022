import type { LoaderArgs } from "@remix-run/node";
import { InactiveUserResult } from "../../models";
import { getSession } from "~/sessions";
import { getCredentials } from "../auth";
import { fetchStats } from "~/utils";

export const loader = async ({ request }: LoaderArgs) => {
  const session = await getSession(request.headers.get("Cookie"));
  const credentialId = session.get("credentialId");
  const { baseUrl, clientId, clientSecret } = await getCredentials(
    credentialId
  );
  return await fetchStats<InactiveUserResult>(
    "/stats/inactive_users",
    baseUrl,
    clientId,
    clientSecret
  );
};
