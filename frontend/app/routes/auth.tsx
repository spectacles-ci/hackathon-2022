import { json } from "@remix-run/node";
import type { ActionFunction } from "@remix-run/node";
import { createCookie } from "@remix-run/node";

const lookerClientIdCookie = createCookie("looker-client-id");

export const action: ActionFunction = async ({ request }) => {
  const cookieHeader = request.headers.get("Cookie");
  const lookerClientId = await lookerClientIdCookie.parse(cookieHeader);

  const formData = await request.formData();
  console.log(formData.get("client_id"));
  return json(
    {},
    {
      headers: {
        "Set-Cookie": await lookerClientIdCookie.serialize(
          formData.get("client_id")
        ),
      },
    }
  );
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
                  htmlFor="password"
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
                  htmlFor="password"
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
                  Roast Me
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
