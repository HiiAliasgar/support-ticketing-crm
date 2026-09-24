import { Inbox, Clock, Loader, CheckCircle2 } from "lucide-react";
import { formatDay } from "../format";

export default function DashboardCards({ data }) {
  if (!data) return null;

  const cards = [
    {
      label: "Total tickets",
      value: data.total,
      icon: Inbox,
      accent: "text-slate-900",
      chip: "bg-slate-100 text-slate-600",
    },
    {
      label: "Open",
      value: data.open_count,
      icon: Clock,
      accent: "text-blue-600",
      chip: "bg-blue-50 text-blue-700",
    },
    {
      label: "In progress",
      value: data.in_progress_count,
      icon: Loader,
      accent: "text-amber-600",
      chip: "bg-amber-50 text-amber-700",
    },
    {
      label: "Closed",
      value: data.closed_count,
      icon: CheckCircle2,
      accent: "text-emerald-600",
      chip: "bg-emerald-50 text-emerald-700",
    },
  ];

  const maxCount = Math.max(...data.tickets_by_day.map((d) => d.count), 1);

  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <div
          key={card.label}
          className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          <span className={`grid h-11 w-11 place-items-center rounded-xl ${card.chip}`}>
            <card.icon size={20} />
          </span>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {card.label}
            </p>
            <p className={`text-2xl font-bold tabular-nums ${card.accent}`}>
              {card.value}
            </p>
          </div>
        </div>
      ))}

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:col-span-2 lg:col-span-1">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
          Last 7 days
        </p>
        <div className="mt-3 flex h-16 items-end justify-between gap-1">
          {data.tickets_by_day.map((day) => (
            <div key={day.date} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-sm bg-indigo-500"
                style={{
                  height: `${Math.max((day.count / maxCount) * 100, 4)}%`,
                }}
                title={`${day.date}: ${day.count}`}
              />
              <span className="text-[10px] text-slate-400">{formatDay(day.date)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}