import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Send } from "lucide-react";
import { createTicket } from "../api";

const emptyForm = {
  customer_name: "",
  customer_email: "",
  subject: "",
  description: "",
};

export default function NewTicketPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState(null);
  const [saving, setSaving] = useState(false);

  const setField = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    setApiError(null);
  };

  const validate = () => {
    const next = {};
    if (!form.customer_name.trim()) next.customer_name = "Customer name is required.";
    if (!form.customer_email.trim()) next.customer_email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.customer_email.trim()))
      next.customer_email = "Enter a valid email address.";
    if (!form.subject.trim()) next.subject = "A short subject is required.";
    if (!form.description.trim()) next.description = "Describe the issue.";
    return next;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    setApiError(null);
    try {
      const created = await createTicket({
        customer_name: form.customer_name.trim(),
        customer_email: form.customer_email.trim(),
        subject: form.subject.trim(),
        description: form.description.trim(),
      });
      navigate(`/tickets/${created.ticket_id}`);
    } catch (err) {
      setApiError(err.message);
      setSaving(false);
    }
  };

  const inputClass = (hasError) =>
    `w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition focus:ring-2 ${
      hasError
        ? "border-red-300 focus:border-red-400 focus:ring-red-100"
        : "border-slate-300 focus:border-indigo-500 focus:ring-indigo-100"
    }`;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-indigo-600"
      >
        <ArrowLeft size={16} /> Back to tickets
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-slate-900">Create a new ticket</h1>
        <p className="text-sm text-slate-500">
          A ticket ID (e.g. TKT-0016) and timestamp are generated automatically.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        noValidate
      >
        {apiError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {apiError}
          </div>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Customer name
            </span>
            <input
              type="text"
              value={form.customer_name}
              onChange={setField("customer_name")}
              placeholder="e.g. Priya Sharma"
              className={inputClass(errors.customer_name)}
            />
            {errors.customer_name && (
              <span className="mt-1 block text-xs text-red-600">{errors.customer_name}</span>
            )}
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">
              Customer email
            </span>
            <input
              type="email"
              value={form.customer_email}
              onChange={setField("customer_email")}
              placeholder="priya@acme.co"
              className={inputClass(errors.customer_email)}
            />
            {errors.customer_email && (
              <span className="mt-1 block text-xs text-red-600">{errors.customer_email}</span>
            )}
          </label>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Issue title
          </span>
          <input
            type="text"
            value={form.subject}
            onChange={setField("subject")}
            placeholder="Short summary of the problem"
            className={inputClass(errors.subject)}
          />
          {errors.subject && (
            <span className="mt-1 block text-xs text-red-600">{errors.subject}</span>
          )}
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Description
          </span>
          <textarea
            value={form.description}
            onChange={setField("description")}
            placeholder="What is the customer experiencing? Relevant steps, context, error messages…"
            rows={5}
            className={inputClass(errors.description)}
          />
          {errors.description && (
            <span className="mt-1 block text-xs text-red-600">{errors.description}</span>
          )}
        </label>

        <div className="flex items-center justify-end gap-3 pt-1">
          <Link
            to="/"
            className="rounded-xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
          >
            <Send size={15} />
            {saving ? "Creating…" : "Create ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}