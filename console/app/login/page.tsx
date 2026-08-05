import { login } from "@/app/actions";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const query = await searchParams;
  return (
    <div className="login">
      <form action={login}>
        <div><h1>TuneGraph</h1><p className="muted">Sign in to the behavior control plane.</p></div>
        {query.error ? <p>Authentication failed.</p> : null}
        <label>Organization<input name="organization_slug" defaultValue="default" required /></label>
        <label>Email<input name="email" type="email" autoComplete="username" required /></label>
        <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
        <button type="submit">Sign in</button>
      </form>
    </div>
  );
}
