import { Link } from "react-router-dom";
import { Inbox } from "lucide-react";
import StatusBadge from "./StatusBadge";
import { formatDate } from "../format";

export default function TicketTable({ tickets }) {
  if (!tickets.length) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <Inbox className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-3 text-sm font-medium text-slate-600">No tickets found</p>
        <p className="mt-1 text-xs text-slate-400">
          Try a different search or filter — or <Link to="/new" className="text-indigo-600 hover:underline">create a ticket</Link>.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Ticket</th>
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">Subject</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {tickets.map((ticket) => (
              <tr key={ticket.ticket_id} className="hover:bg-slate-50 transition">
                <td className="whitespace-nowrap px-4 py-3">
                  <Link
                    to={`/tickets/${ticket.ticket_id}`}
                    className="font-mono text-xs font-medium text-indigo-600 hover:underline"
                  >
                    {ticket.ticket_id}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                  {ticket.customer_name}
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`/tickets/${ticket.ticket_id}`}
                    className="font-medium text-slate-900 hover:text-indigo-600 transition"
                  >
                    {ticket.subject}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge status={ticket.status} />
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                  {formatDate(ticket.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}