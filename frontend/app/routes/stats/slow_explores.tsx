import type { LoaderArgs } from "@remix-run/node";
import { SlowExploresResult } from "../../models";
import { getSession } from "~/sessions";
import { getCredentials } from "../auth";
import { fetchStats } from "~/utils";

export const loader = async ({ request }: LoaderArgs) => {
  const session = await getSession(request.headers.get("Cookie"));
  const credentialId = session.get("credentialId");
  const { baseUrl, clientId, clientSecret } = await getCredentials(
    credentialId
  );
  return await fetchStats<SlowExploresResult>(
    "/stats/slow_explores",
    baseUrl,
    clientId,
    clientSecret
  );
};
