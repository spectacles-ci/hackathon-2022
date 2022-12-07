import { json } from "@remix-run/node";
import { InactiveUserResult } from "../../models";

export const loader = async () => {
  const response = await fetch(`${process.env.API_URL}/stats/inactive_users`, {
    method: "POST",
    body: JSON.stringify({
      host_url: process.env.LOOKER_BASE_URL,
      port: 19999,
      client_id: process.env.LOOKER_CLIENT_ID,
      client_secret: process.env.LOOKER_CLIENT_SECRET,
    }),
    headers: { "Content-Type": "application/json" },
  });
  return json<InactiveUserResult>(await response.json());
};
