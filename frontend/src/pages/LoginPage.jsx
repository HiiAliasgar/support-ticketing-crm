import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username.trim(), password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const inputClass =
    "w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="text-center">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-indigo-600 text-white shadow-sm">
          <ShieldCheck size={22} />
        </span>
        <h1 className="mt-4 text-2xl font-bold text-slate-900">Staff sign in</h1>
        <p className="mt-1 text-sm text-slate-500">
          Admins manage agents, settings, and exports. Agents assign tickets.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className={inputClass}
            placeholder="admin"
          />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className={inputClass}
            placeholder="••••••••"
          />
        </label>
        <button
          type="submit"
          disabled={busy || !username || !password}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
        >
          <LogIn size={15} /> {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-center text-xs text-slate-500">
        Demo console access — admin: <code className="font-mono text-slate-700">admin</code> /
        <code className="font-mono text-slate-700">SupportTick2026!</code> &nbsp;·&nbsp; agent:{" "}
        <code className="font-mono text-slate-700">riley</code> /
        <code className="font-mono text-slate-700">agent123456</code>
        <br />
        <Link to="/" className="mt-1 inline-block text-indigo-600 hover:underline">
          ← Back to tickets
        </Link>
      </p>
    </div>
  );
}