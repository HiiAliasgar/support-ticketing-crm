const STYLES = {
  Open: "bg-blue-50 text-blue-700 ring-blue-200",
  "In Progress": "bg-amber-50 text-amber-700 ring-amber-200",
  Closed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
        STYLES[status] ?? "bg-slate-50 text-slate-600 ring-slate-200"
      }`}
    >
      {status}
    </span>
  );
}