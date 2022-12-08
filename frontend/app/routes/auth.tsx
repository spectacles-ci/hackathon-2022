import { redirect, json } from "@remix-run/node";
import type { ActionFunction, LoaderArgs } from "@remix-run/node";
import { createCookie } from "@remix-run/node";
import { SecretManagerServiceClient } from "@google-cloud/secret-manager";
import crypto from "crypto";
import { getSession, commitSession } from "../sessions";

async function storeCredentials(
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

export async function loader({ request }: LoaderArgs) {
  // const session = await getSession(request.headers.get("Cookie"));
  // if (session.has("credentialId")) {
  //   return redirect("/roast");
  // }
  return null;
}

export const action: ActionFunction = async ({ request }) => {
  const session = await getSession(request.headers.get("Cookie"));
  const formData = await request.formData();
  const secretId = await storeCredentials(
    formData.get("instance_url"),
    formData.get("client_id"),
    formData.get("client_secret")
  );
  session.set("credentialId", secretId);
  return redirect("/roast", {
    headers: { "Set-Cookie": await commitSession(session) },
  });
};

export default function Auth() {
  return (
    <>
      <div className="flex min-h-full flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Roast My Looker Instance
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter your Looker API credentials to get started.
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <form className="space-y-6" action="#" method="post">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-700"
                >
                  Work email
                </label>
                <div className="mt-1">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="instance_url"
                  className="block text-sm font-medium text-gray-700"
                >
                  Looker instance URL
                </label>
                <div className="mt-1">
                  <input
                    id="instance_url"
                    name="instance_url"
                    type="text"
                    placeholder="e.g. https://spectacles.looker.com"
                    required
                    className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="client_id"
                  className="block text-sm font-medium text-gray-700"
                >
                  Client ID
                </label>
                <div className="mt-1">
                  <input
                    id="client_id"
                    name="client_id"
                    type="text"
                    required
                    className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="client_secret"
                  className="block text-sm font-medium text-gray-700"
                >
                  Client secret
                </label>
                <div className="mt-1">
                  <input
                    id="client_secret"
                    name="client_secret"
                    type="password"
                    required
                    className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="flex w-full justify-center rounded-md border border-transparent bg-indigo-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                >
                  🔥 Roast Me
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
