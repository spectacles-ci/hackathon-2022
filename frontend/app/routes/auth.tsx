import { redirect } from "@remix-run/node";
import type { ActionFunction, LoaderArgs } from "@remix-run/node";
import { getSession, commitSession } from "../sessions";
import { storeCredentials } from "~/utils";

export async function loader({ request }: LoaderArgs) {
  const session = await getSession(request.headers.get("Cookie"));
  if (session.has("credentialId")) {
    return redirect("/roast");
  }
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
          <h1 className="mt-6 text-center text-4xl font-bold tracking-tight text-gray-900">
            Roast My Looker Instance
          </h1>
          <p className="px-4 mt-8 text-center text-sm text-gray-600 leading-relaxed">
            We'll run some queries to see if your Looker instance is running as
            smoothly as you think it is.
          </p>
          <p className="px-4 mt-4 text-center text-sm text-gray-600 leading-relaxed">
            Enter API credentials for a Looker user with the Admin role or
            Developer role + the{" "}
            <span className="bg-gray-200 rounded text-gray-500 p-0.5 font-mono text-sm">
              see_system_activity
            </span>{" "}
            permission.*
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <form className="space-y-6" action="/auth" method="post">
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
                    minLength={20}
                    maxLength={20}
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
                    minLength={24}
                    maxLength={24}
                    className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="flex w-full justify-center rounded-md border border-transparent bg-indigo-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                >
                  🔥 Let's Roast
                </button>
              </div>
            </form>
          </div>
          <p className="mt-8 text-center text-xs text-gray-500 leading-normal">
            Why? We need credentials for an Admin user so we can query the{" "}
            <a
              className="underline"
              href="https://cloud.google.com/looker/docs/system-activity-pages"
            >
              System Activity Explore
            </a>
            . Don't worry, we'll keep them encrypted and won't store them.
          </p>
        </div>
        <p className="mt-8 pb-8 text-center text-xs text-gray-500">
          Built with ❤️ (and snark) by the team at{" "}
          <a className="underline" href="https://spectacles.dev">
            Spectacles
          </a>
        </p>
      </div>
    </>
  );
}
