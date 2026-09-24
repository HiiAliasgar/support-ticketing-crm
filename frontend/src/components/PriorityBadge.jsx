const STYLES = {
  Low: "bg-slate-100 text-slate-600 ring-slate-300",
  Medium: "bg-blue-50 text-blue-700 ring-blue-200",
  High: "bg-amber-50 text-amber-700 ring-amber-300",
  Urgent: "bg-red-50 text-red-700 ring-red-300",
};

export default function PriorityBadge({ priority }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
        STYLES[priority] ?? "bg-slate-50 text-slate-600 ring-slate-200"
      }`}
    >
      {priority ?? "Medium"}
    </span>
  );
}