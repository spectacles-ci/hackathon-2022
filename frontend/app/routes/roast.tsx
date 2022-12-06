import { json } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import { components } from "../schema";

type InactiveUserResult = components["schemas"]["InactiveUserResult"];

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

export default function Roast() {
  const data = useLoaderData() as InactiveUserResult;
  return (
    <div className="mx-auto max-w-7xl sm:px-6 lg:px-8">
      <h1>Hello World!</h1>
      <p>
        {data.pct_inactive}% of your users are inactive, that's {data.grade}.
      </p>
    </div>
  );
}
