import React from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Layers, LifeBuoy, LogIn, LogOut, ShieldCheck, User } from "lucide-react";
import { useAuth } from "./auth.jsx";
import HomePage from "./pages/HomePage.jsx";
import NewTicketPage from "./pages/NewTicketPage.jsx";
import TicketDetailPage from "./pages/TicketDetailPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";

const navLinkClass = ({ isActive }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
    isActive ? "bg-indigo-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
  }`;

function RequireAdmin({ children }) {
  const { user, isAdmin, ready } = useAuth();
  if (!ready) return null;
  if (!user)
    return (
      <Navigate to="/login" replace state={{ from: "/admin" }} />
    );
  if (!isAdmin)
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <ShieldCheck className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-3 text-lg font-medium text-slate-700">Admins only</p>
        <p className="mt-1 text-sm text-slate-500">
          Sign in with an admin account to open the admin console.
        </p>
        <Link to="/" className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:underline">
          Back to tickets
        </Link>
      </div>
    );
  return children;
}

export default function App() {
  const { user, isAdmin, logout, ready } = useAuth();

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <LifeBuoy size={18} />
            </span>
            <span className="leading-tight">
              <span className="block text-base font-semibold text-slate-900">SupportTick</span>
              <span className="hidden text-xs text-slate-400 sm:block">
                Customer Support CRM
              </span>
            </span>
          </Link>
          <nav className="flex items-center gap-2">
            <NavLink to="/" end className={navLinkClass}>
              <span className="flex items-center gap-1.5">
                <Layers size={15} /> Tickets
              </span>
            </NavLink>
            <NavLink to="/new" className={navLinkClass}>
              New Ticket
            </NavLink>
            {isAdmin && (
              <NavLink to="/admin" className={navLinkClass}>
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={15} /> Admin
                </span>
              </NavLink>
            )}
            {user ? (
              <div className="ml-2 flex items-center gap-2 rounded-full border border-slate-200 bg-white pl-1.5 pr-1 py-1">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                  {(user.display_name ?? user.username).charAt(0).toUpperCase()}
                </span>
                <span className="hidden text-xs font-medium text-slate-700 sm:block">
                  {user.display_name ?? user.username}
                  <span className="ml-1.5 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
                    {user.role}
                  </span>
                </span>
                <button
                  onClick={logout}
                  title="Sign out"
                  className="grid h-7 w-7 place-items-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                >
                  <LogOut size={14} />
                </button>
              </div>
            ) : (
              <NavLink
                to="/login"
                className="ml-2 inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                <LogIn size={14} /> Sign in
              </NavLink>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/new" element={<NewTicketPage />} />
          <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
          <Route
            path="/login"
            element={user ? <Navigate to="/" replace /> : <LoginPage />}
          />
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <AdminPage />
              </RequireAdmin>
            }
          />
          <Route
            path="*"
            element={
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
                <p className="text-lg font-medium text-slate-700">Page not found</p>
                <Link to="/" className="mt-2 inline-block text-sm text-indigo-600 hover:underline">
                  Back to tickets
                </Link>
              </div>
            }
          />
        </Routes>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-center gap-1.5 px-4 py-4 text-xs text-slate-400">
          <User size={12} />
          SupportTick CRM — FastAPI + SQLite + React. Built as a full-stack capstone.
        </div>
      </footer>
    </div>
  );
}