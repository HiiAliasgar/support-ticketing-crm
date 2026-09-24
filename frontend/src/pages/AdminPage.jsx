import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Download,
  Plus,
  Save,
  Settings as SettingsIcon,
  Users,
} from "lucide-react";
import {
  adminAudit,
  adminCreateAgent,
  adminExportCsv,
  adminGetSettings,
  adminListAgents,
  adminUpdateAgent,
  adminUpdateSettings,
  getDashboard,
} from "../api";
import Spinner from "../components/Spinner";
import { formatDate } from "../format";

const TABS = [
  { key: "agents", label: "Agents", icon: Users },
  { key: "settings", label: "Settings", icon: SettingsIcon },
  { key: "audit", label: "Audit log", icon: Activity },
];

const inputClass =
  "w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";

export default function AdminPage() {
  const [tab, setTab] = useState("agents");
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // agents tab
  const [agents, setAgents] = useState([]);
  const [newAgent, setNewAgent] = useState({ username: "", display_name: "", password: "" });
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [agentError, setAgentError] = useState(null);

  // settings tab
  const [settings, setSettings] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);

  // audit tab
  const [audit, setAudit] = useState(null);
  const [auditPage, setAuditPage] = useState(1);

  // priority summary
  const [byPriority, setByPriority] = useState(null);

  const showFeedback = (message, ok = true) => {
    setFeedback({ message, ok });
    setTimeout(() => setFeedback(null), 3000);
  };

  const refreshAgents = useCallback(() => {
    adminListAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const refreshSettings = useCallback(() => {
    adminGetSettings().then(setSettings).catch(() => setSettings(null));
  }, []);

  const refreshAudit = useCallback(() => {
    adminAudit(auditPage, 25).then(setAudit).catch(() => setAudit(null));
  }, [auditPage]);

  useEffect(() => {
    getDashboard()
      .then((d) => setByPriority(d.by_priority ?? null))
      .catch(() => setByPriority(null));
    refreshAgents();
    refreshSettings();
    setLoading(false);
  }, [refreshAgents, refreshSettings]);

  useEffect(() => {
    if (tab === "audit") refreshAudit();
  }, [tab, refreshAudit]);

  const handleCreateAgent = async (e) => {
    e.preventDefault();
    setAgentError(null);
    setCreatingAgent(true);
    try {
      await adminCreateAgent(newAgent);
      setNewAgent({ username: "", display_name: "", password: "" });
      refreshAgents();
      showFeedback("Agent created");
    } catch (err) {
      setAgentError(err.message);
    } finally {
      setCreatingAgent(false);
    }
  };

  const handleToggleAgent = async (agent) => {
    try {
      await adminUpdateAgent(agent.id, { active: !agent.active });
      refreshAgents();
      showFeedback(`${agent.username} ${agent.active ? "disabled" : "enabled"}`);
    } catch (err) {
      showFeedback(`Failed: ${err.message}`, false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      await adminUpdateSettings(settings);
      setSettings((await adminGetSettings()));
      showFeedback("Settings saved");
    } catch (err) {
      showFeedback(`Failed: ${err.message}`, false);
    } finally {
      setSavingSettings(false);
    }
  };

  const handleExport = async () => {
    try {
      const csv = await adminExportCsv();
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tickets-export-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showFeedback("Export downloaded");
    } catch (err) {
      showFeedback(`Failed: ${err.message}`, false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin console</h1>
          <p className="text-sm text-slate-500">Manage the support team, settings, and activity.</p>
        </div>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-700"
        >
          <Download size={15} /> Export CSV
        </button>
      </div>

      {feedback && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            feedback.ok
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {feedback.message}
        </div>
      )}

      {byPriority && (
        <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Tickets by priority
          </span>
          {["Urgent", "High", "Medium", "Low"].map((level) => (
            <span key={level} className="flex items-center gap-1.5 text-sm text-slate-600">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  level === "Urgent"
                    ? "bg-red-500"
                    : level === "High"
                      ? "bg-amber-500"
                      : level === "Medium"
                        ? "bg-blue-500"
                        : "bg-slate-400"
                }`}
              />
              {level}: <b>{byPriority[level] ?? 0}</b>
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium ring-1 ring-inset transition ${
              tab === t.key
                ? "bg-indigo-600 text-white ring-indigo-600"
                : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50"
            }`}
          >
            <t.icon size={15} /> {t.label}
          </button>
        ))}
      </div>

      {tab === "agents" && (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Username</th>
                    <th className="px-4 py-3 font-medium">Display name</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {agents.map((agent) => (
                    <tr key={agent.id} className="hover:bg-slate-50 transition">
                      <td className="px-4 py-3 font-medium text-slate-900">{agent.username}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {agent.display_name ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{agent.role}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
                            agent.active
                              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                              : "bg-slate-100 text-slate-500 ring-slate-300"
                          }`}
                        >
                          {agent.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {agent.role === "admin" ? (
                          <span className="text-xs text-slate-300">Protected</span>
                        ) : (
                          <button
                            onClick={() => handleToggleAgent(agent)}
                            className="text-xs font-medium text-indigo-600 hover:underline"
                          >
                            {agent.active ? "Disable" : "Enable"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <form
            onSubmit={handleCreateAgent}
            className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-4"
          >
            <input
              type="text"
              value={newAgent.username}
              onChange={(e) => setNewAgent({ ...newAgent, username: e.target.value })}
              placeholder="Username"
              required
              className={inputClass}
            />
            <input
              type="text"
              value={newAgent.display_name}
              onChange={(e) => setNewAgent({ ...newAgent, display_name: e.target.value })}
              placeholder="Display name"
              className={inputClass}
            />
            <input
              type="password"
              value={newAgent.password}
              minLength={8}
              onChange={(e) => setNewAgent({ ...newAgent, password: e.target.value })}
              placeholder="Password (min 8)"
              required
              className={inputClass}
            />
            <button
              type="submit"
              disabled={creatingAgent || !newAgent.username || !newAgent.password}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
            >
              <Plus size={15} /> {creatingAgent ? "Adding…" : "Add agent"}
            </button>
            {agentError && <p className="text-xs text-red-600 sm:col-span-4">{agentError}</p>}
          </form>
        </div>
      )}

      {tab === "settings" && settings && (
        <form
          onSubmit={handleSaveSettings}
          className="max-w-lg space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">Workspace name</span>
            <input
              type="text"
              value={settings.workspace_name ?? ""}
              onChange={(e) => setSettings({ ...settings, workspace_name: e.target.value })}
              className={inputClass}
            />
          </label>
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Ticket prefix</span>
              <input
                type="text"
                value={settings.ticket_prefix ?? ""}
                maxLength={6}
                onChange={(e) =>
                  setSettings({ ...settings, ticket_prefix: e.target.value.toUpperCase() })
                }
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">SLA hours</span>
              <input
                type="number"
                min={1}
                value={settings.sla_hours ?? 24}
                onChange={(e) => setSettings({ ...settings, sla_hours: Number(e.target.value) })}
                className={inputClass}
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">Default note author</span>
            <input
              type="text"
              value={settings.default_note_author ?? ""}
              onChange={(e) => setSettings({ ...settings, default_note_author: e.target.value })}
              className={inputClass}
            />
          </label>
          <button
            type="submit"
            disabled={savingSettings}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
          >
            <Save size={15} /> {savingSettings ? "Saving…" : "Save settings"}
          </button>
        </form>
      )}

      {tab === "audit" && (
        <div className="space-y-4">
          {audit && audit.items.length ? (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-medium">When</th>
                      <th className="px-4 py-3 font-medium">User</th>
                      <th className="px-4 py-3 font-medium">Action</th>
                      <th className="px-4 py-3 font-medium">Target</th>
                      <th className="px-4 py-3 font-medium">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {audit.items.map((entry) => (
                      <tr key={entry.id} className="hover:bg-slate-50 transition">
                        <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                          {formatDate(entry.created_at)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                          {entry.username ?? "system"}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                            {entry.action}
                          </code>
                        </td>
                        <td className="px-4 py-3 text-slate-600">{entry.target_type ?? "—"}</td>
                        <td className="max-w-md px-4 py-3 text-xs text-slate-500">
                          <span className="line-clamp-2">{entry.detail}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
              No audit entries yet.
            </p>
          )}
          {audit && audit.pages > 1 && (
            <div className="flex items-center justify-between text-sm">
              <p className="text-xs text-slate-500">
                Page {audit.page} of {audit.pages} · {audit.total} entries
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setAuditPage((p) => Math.max(p - 1, 1))}
                  disabled={audit.page <= 1}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
                >
                  Prev
                </button>
                <button
                  onClick={() => setAuditPage((p) => Math.min(p + 1, audit.pages))}
                  disabled={audit.page >= audit.pages}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}