import { redirect } from "@remix-run/node";

export async function loader() {
  return redirect("/auth");
}

export default function Index() {
  return null;
}
