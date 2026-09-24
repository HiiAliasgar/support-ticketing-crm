import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, X } from "lucide-react";
import { getDashboard, listTickets } from "../api";
import DashboardCards from "../components/DashboardCards";
import TicketTable from "../components/TicketTable";
import Spinner from "../components/Spinner";

const STATUS_FILTERS = ["All", "Open", "In Progress", "Closed"];

export default function HomePage() {
  const [tickets, setTickets] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All");

  useEffect(() => {
    getDashboard()
      .then(setDashboard)
      .catch(() => setDashboard(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(
      () => {
        setLoading(true);
        setError(null);
        listTickets({
          search,
          status: status === "All" ? undefined : status,
        })
          .then((data) => {
            if (!cancelled) setTickets(data);
          })
          .catch((err) => {
            if (!cancelled) {
              setError(err.message);
              setTickets([]);
            }
          })
          .finally(() => {
            if (!cancelled) setLoading(false);
          });
      },
      search ? 250 : 0
    );
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tickets</h1>
          <p className="text-sm text-slate-500">
            Search, filter, and manage support requests.
          </p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700"
        >
          <Plus size={16} /> New ticket
        </Link>
      </div>

      <DashboardCards data={dashboard} />

      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-xs">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, email, ID, subject…"
              aria-label="Search tickets"
              className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-8 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-slate-600"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter}
                onClick={() => setStatus(filter)}
                className={`rounded-full px-3.5 py-1.5 text-xs font-medium ring-1 ring-inset transition ${
                  status === filter
                    ? "bg-slate-900 text-white ring-slate-900"
                    : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? <Spinner /> : <TicketTable tickets={tickets} />}
      </div>
    </div>
  );
}