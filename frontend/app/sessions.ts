import { createCookieSessionStorage } from "@remix-run/node"; // or cloudflare/deno

const { getSession, commitSession, destroySession } =
  createCookieSessionStorage({
    cookie: {
      name: "__session",
      domain: process.env.COOKIE_DOMAIN,
      httpOnly: false,
      maxAge: 86400,
      sameSite: "lax",
      secure: true,
    },
  });

export { getSession, commitSession, destroySession };
