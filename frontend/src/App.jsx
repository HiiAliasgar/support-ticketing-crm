import React from "react";
import { BrowserRouter, Link, NavLink, Routes, Route } from "react-router-dom";
import { LifeBuoy, Layers } from "lucide-react";
import HomePage from "./pages/HomePage.jsx";
import NewTicketPage from "./pages/NewTicketPage.jsx";
import TicketDetailPage from "./pages/TicketDetailPage.jsx";

const navLinkClass = ({ isActive }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
    isActive
      ? "bg-indigo-600 text-white shadow-sm"
      : "text-slate-600 hover:bg-slate-100"
  }`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <LifeBuoy size={18} />
            </span>
            <span className="leading-tight">
              <span className="block text-base font-semibold text-slate-900">
                SupportTick
              </span>
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
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/new" element={<NewTicketPage />} />
          <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
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
        <div className="mx-auto max-w-6xl px-4 py-4 text-center text-xs text-slate-400">
          SupportTick CRM — FastAPI + SQLite + React. Built as a full-stack capstone.
        </div>
      </footer>
    </div>
  );
}