import Link from "next/link";
import { logout } from "@/app/actions";

export function Nav() {
  return (
    <aside className="sidebar">
      <div className="brand">TuneGraph</div>
      <nav>
        <Link href="/">Overview</Link>
        <Link href="/patches">Patches</Link>
        <Link href="/graphs">Graphs</Link>
        <Link href="/deployments">Deployments</Link>
      </nav>
      <form action={logout}><button className="secondary">Sign out</button></form>
    </aside>
  );
}
