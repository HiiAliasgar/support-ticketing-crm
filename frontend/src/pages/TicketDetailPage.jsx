import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Mail, MessageSquarePlus, Send, User } from "lucide-react";
import { addNote, getTicket, updateTicket } from "../api";
import StatusBadge from "../components/StatusBadge";
import Spinner from "../components/Spinner";
import { formatDate } from "../format";

const STATUSES = ["Open", "In Progress", "Closed"];

export default function TicketDetailPage() {
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [status, setStatus] = useState("Open");
  const [statusSaving, setStatusSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const [noteText, setNoteText] = useState("");
  const [author, setAuthor] = useState("Agent");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteError, setNoteError] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getTicket(ticketId)
      .then((data) => {
        setTicket(data);
        setStatus(data.status);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [ticketId]);

  const handleStatusUpdate = async () => {
    if (!ticket || status === ticket.status) return;
    setStatusSaving(true);
    setStatusMessage(null);
    try {
      const result = await updateTicket(ticketId, { status });
      setTicket((prev) => ({ ...prev, status, updated_at: result.updated_at }));
      setStatusMessage("Status updated");
      setTimeout(() => setStatusMessage(null), 2500);
    } catch (err) {
      setStatusMessage(`Failed: ${err.message}`);
    } finally {
      setStatusSaving(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    setNoteSaving(true);
    setNoteError(null);
    try {
      await addNote(ticketId, { note_text: noteText.trim(), author: author.trim() || "Agent" });
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
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-indigo-600"
      >
        <ArrowLeft size={16} /> Back to tickets
      </Link>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900">{ticket.subject}</h1>
              <StatusBadge status={ticket.status} />
            </div>
            <p className="mt-1 font-mono text-sm text-slate-500">
              {ticket.ticket_id}
            </p>
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
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">
                Update status
              </dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <select
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setStatusMessage(null);
                  }}
                  className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleStatusUpdate}
                  disabled={statusSaving || status === ticket.status}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
                >
                  <Check size={15} /> {statusSaving ? "Saving…" : "Save"}
                </button>
                {statusMessage && (
                  <span
                    className={`text-xs ${
                      statusMessage.startsWith("Failed") ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {statusMessage}
                  </span>
                )}
              </dd>
            </div>
          </div>
        </dl>

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