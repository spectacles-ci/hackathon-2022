import { json, TypedResponse } from "@remix-run/node";
import { SecretManagerServiceClient } from "@google-cloud/secret-manager";
import crypto from "crypto";

export async function storeCredentials(
  baseUrl: string,
  clientId: string,
  clientSecret: string
) {
  const client = new SecretManagerServiceClient();
  const secretId = crypto.createHash("md5").update(baseUrl).digest("hex");
  const [secret] = await client.createSecret({
    parent: `projects/${process.env.GOOGLE_CLOUD_PROJECT}`,
    secretId,
    secret: {
      replication: { automatic: {} },
      ttl: {
        seconds: 86400,
      },
    },
  });
  const [version] = await client.addSecretVersion({
    parent: secret.name,
    payload: {
      data: Buffer.from(
        JSON.stringify({
          baseUrl,
          clientId,
          clientSecret,
        }),
        "utf-8"
      ),
    },
  });
  return secretId;
}

export async function getCredentials(credentialId: string) {
  const client = new SecretManagerServiceClient();
  const [version] = await client.accessSecretVersion({
    name: `projects/${process.env.GOOGLE_CLOUD_PROJECT}/secrets/${credentialId}/versions/1`,
  });
  return JSON.parse(version.payload.data.toString());
}

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
