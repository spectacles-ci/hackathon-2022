import { json, TypedResponse } from "@remix-run/node";

export async function fetchStats<T>(
  route: string,
  baseUrl: string,
  clientId: string,
  clientSecret: string
): Promise<TypedResponse<T>> {
  const response = await fetch(`${process.env.API_URL}${route}`, {
    method: "POST",
    body: JSON.stringify({
      host_url: baseUrl,
      port: 19999,
      client_id: clientId,
      client_secret: clientSecret,
    }),
    headers: { "Content-Type": "application/json" },
  });
  return json<T>(await response.json());
}
