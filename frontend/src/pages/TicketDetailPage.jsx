import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  Mail,
  MessageSquarePlus,
  Send,
  Trash2,
  User,
  UserCheck,
} from "lucide-react";
import {
  addNote,
  assignTicket,
  deleteTicket,
  getTicket,
  listAgents,
  updateTicket,
} from "../api";
import { useAuth } from "../auth";
import StatusBadge from "../components/StatusBadge";
import PriorityBadge from "../components/PriorityBadge";
import Spinner from "../components/Spinner";
import { formatDate } from "../format";

const STATUSES = ["Open", "In Progress", "Closed"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];

export default function TicketDetailPage() {
  const { ticketId } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [status, setStatus] = useState("Open");
  const [priority, setPriority] = useState("Medium");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  const [assigneeId, setAssigneeId] = useState("");
  const [assignSaving, setAssignSaving] = useState(false);
  const [assignMessage, setAssignMessage] = useState(null);

  const [noteText, setNoteText] = useState("");
  const [author, setAuthor] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteError, setNoteError] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteMessage, setDeleteMessage] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getTicket(ticketId)
      .then((data) => {
        setTicket(data);
        setStatus(data.status);
        setPriority(data.priority ?? "Medium");
        setAssigneeId(data.assignee_id ? String(data.assignee_id) : "");
        if (!author) setAuthor(data.assignee_name ?? "Agent");
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    if (!author && user?.display_name) setAuthor(user.display_name);
  }, [user, author]);

  useEffect(load, [ticketId]);

  const handleSave = async () => {
    if (!ticket || (status === ticket.status && priority === (ticket.priority ?? "Medium"))) {
      return;
    }
    setSaving(true);
    setSaveMessage(null);
    try {
      const result = await updateTicket(ticketId, { status, priority });
      setTicket((prev) => ({ ...prev, status, priority, updated_at: result.updated_at }));
      setSaveMessage("Saved");
      setTimeout(() => setSaveMessage(null), 2500);
    } catch (err) {
      setSaveMessage(`Failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAssign = async () => {
    if (!assigneeId && !ticket.assignee_id) return;
    setAssignSaving(true);
    setAssignMessage(null);
    try {
      const result = await assignTicket(ticketId, assigneeId ? Number(assigneeId) : null);
      setTicket((prev) => ({
        ...prev,
        assignee_id: result.assignee_id,
        assignee_name: result.assignee_name,
        updated_at: result.updated_at,
      }));
      setAssignMessage("Assignee saved");
      setTimeout(() => setAssignMessage(null), 2500);
    } catch (err) {
      setAssignMessage(`Failed: ${err.message}`);
    } finally {
      setAssignSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${ticket.ticket_id} permanently? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await deleteTicket(ticketId);
      navigate("/");
    } catch (err) {
      setDeleteMessage(err.message);
      setDeleting(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    setNoteSaving(true);
    setNoteError(null);
    try {
      await addNote(ticketId, {
        note_text: noteText.trim(),
        author: author.trim() || "Agent",
      });
      setNoteText("");
      await load();
    } catch (err) {
      setNoteError(err.message);
    } finally {
      setNoteSaving(false);
    }
  };

  if (loading) return <Spinner />;

  if (error || !ticket) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="text-lg font-medium text-slate-700">
          {error ?? "Ticket not found"}
        </p>
        <Link to="/" className="mt-3 inline-block text-sm font-medium text-indigo-600 hover:underline">
          Back to tickets
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-indigo-600"
        >
          <ArrowLeft size={16} /> Back to tickets
        </Link>
        {isAdmin && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 transition hover:bg-red-100 disabled:opacity-50"
          >
            <Trash2 size={15} /> {deleting ? "Deleting…" : "Delete ticket"}
          </button>
        )}
        {deleteMessage && (
          <span className="text-xs text-red-600">{deleteMessage}</span>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900">{ticket.subject}</h1>
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
            </div>
            <p className="mt-1 font-mono text-sm text-slate-500">{ticket.ticket_id}</p>
          </div>
          <div className="text-right text-xs text-slate-400">
            <p>Created {formatDate(ticket.created_at)}</p>
            <p>Updated {formatDate(ticket.updated_at)}</p>
          </div>
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-indigo-50 text-indigo-600">
              <User size={16} />
            </span>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Customer</dt>
              <dd className="text-sm font-medium text-slate-800">{ticket.customer_name}</dd>
              <dd className="text-sm text-slate-500">
                <a
                  href={`mailto:${ticket.customer_email}`}
                  className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
                >
                  <Mail size={13} /> {ticket.customer_email}
                </a>
              </dd>
            </div>
          </div>

          <div className="flex items-start gap-3 sm:justify-end">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-slate-500">
              <UserCheck size={16} />
            </span>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Assignee</dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <select
                  value={assigneeId}
                  onChange={(e) => {
                    setAssigneeId(e.target.value);
                    setAssignMessage(null);
                  }}
                  className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="">Unassigned</option>
                  {agents
                    .filter((a) => a.active)
                    .map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.display_name ?? agent.username}
                      </option>
                    ))}
                </select>
                <button
                  onClick={handleAssign}
                  disabled={assignSaving}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
                >
                  <Check size={15} /> {assignSaving ? "Saving…" : "Assign"}
                </button>
                {assignMessage && (
                  <span
                    className={`text-xs ${
                      assignMessage.startsWith("Failed") ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {assignMessage}
                  </span>
                )}
              </dd>
            </div>
          </div>
        </dl>

        <div className="mt-5 flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 pt-5">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-slate-400">
              Status
              <select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setSaveMessage(null);
                }}
                className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm normal-case shadow-sm outline-none focus:border-indigo-500"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-slate-400">
              Priority
              <select
                value={priority}
                onChange={(e) => {
                  setPriority(e.target.value);
                  setSaveMessage(null);
                }}
                className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm normal-case shadow-sm outline-none focus:border-indigo-500"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={handleSave}
              disabled={saving || (status === ticket.status && priority === (ticket.priority ?? "Medium"))}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              <Check size={15} /> {saving ? "Saving…" : "Save"}
            </button>
            {saveMessage && (
              <span
                className={`text-xs ${
                  saveMessage.startsWith("Failed") ? "text-red-600" : "text-emerald-600"
                }`}
              >
                {saveMessage}
              </span>
            )}
          </div>
        </div>

        <div className="mt-6 border-t border-slate-100 pt-5">
          <h2 className="text-sm font-semibold text-slate-700">Description</h2>
          <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600">
            {ticket.description}
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <MessageSquarePlus size={16} className="text-indigo-600" />
          Notes & activity
        </h2>

        {ticket.notes.length ? (
          <ul className="mt-4 space-y-4">
            {ticket.notes.map((note) => (
              <li key={note.id} className="rounded-xl bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-slate-700">{note.author}</span>
                  <span className="text-slate-400">{formatDate(note.created_at)}</span>
                </div>
                <p className="mt-1.5 whitespace-pre-line text-sm text-slate-600">
                  {note.note_text}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-slate-400">No notes yet. Add the first one below.</p>
        )}

        <form onSubmit={handleAddNote} className="mt-5 space-y-3">
          {noteError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {noteError}
            </div>
          )}
          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Add an internal note, next step, or resolution…"
            rows={3}
            className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <User size={14} className="text-slate-400" />
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="Your name"
                className="w-36 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500"
              />
            </label>
            <button
              type="submit"
              disabled={noteSaving || !noteText.trim()}
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
            >
              <Send size={15} /> {noteSaving ? "Adding…" : "Add note"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}