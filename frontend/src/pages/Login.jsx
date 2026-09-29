import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const DEMO = [
  { username: "admin", password: "admin123", label: "I4C national admin" },
  { username: "tn_lea", password: "lea123", label: "Tamil Nadu LEA" },
  { username: "hdfc_officer", password: "bank123", label: "HDFC bank officer" },
];

export default function Login() {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Login failed");
    }
  };

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-bg px-4 py-10">
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-blue-100 blur-3xl" aria-hidden="true" />
      <div className="absolute -bottom-40 -right-32 h-96 w-96 rounded-full bg-cyan-100 blur-3xl" aria-hidden="true" />
      <section className="relative w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/60" aria-labelledby="login-title">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-accent text-white">
            <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
          <div><h1 id="login-title" className="text-3xl font-extrabold tracking-tight text-text">VIZHI</h1><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Predict. Prevent. Protect.</p></div>
        </div>
        <p className="mb-6 text-sm text-muted">Secure access to predictive cash-withdrawal intelligence for I4C, law enforcement, and financial institutions.</p>

        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-semibold"><span className="mb-1.5 block">Username</span><input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 focus:border-accent" /></label>
          <label className="block text-sm font-semibold"><span className="mb-1.5 block">Password</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 focus:border-accent" /></label>
          {error && <div className="rounded-lg bg-red-50 p-3 text-sm font-medium text-danger" role="alert">{error}</div>}
          <button disabled={loading} className="min-h-12 w-full rounded-xl bg-accent font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50">{loading ? "Authenticating…" : "Secure login"}</button>
        </form>

        <div className="mt-6 border-t border-slate-200 pt-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Demo roles</div>
          <div className="space-y-2">{DEMO.map((demo) => <button key={demo.username} onClick={() => { setUsername(demo.username); setPassword(demo.password); }} className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-left text-sm text-muted hover:border-blue-200 hover:bg-blue-50 hover:text-accent"><span className="font-semibold">{demo.label}</span> · {demo.username}</button>)}</div>
        </div>
        <p className="mt-6 text-center text-xs text-muted">SIH 26184 · Ministry of Home Affairs · I4C</p>
      </section>
    </main>
  );
}
