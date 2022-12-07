import { json } from "@remix-run/node";
import { AbandonedDashboardResult } from "../../models";

export const loader = async () => {
  const response = await fetch(
    `${process.env.API_URL}/stats/abandoned_dashboards`,
    {
      method: "POST",
      body: JSON.stringify({
        host_url: process.env.LOOKER_BASE_URL,
        port: 19999,
        client_id: process.env.LOOKER_CLIENT_ID,
        client_secret: process.env.LOOKER_CLIENT_SECRET,
      }),
      headers: { "Content-Type": "application/json" },
    }
  );
  return json<AbandonedDashboardResult>(await response.json());
};
