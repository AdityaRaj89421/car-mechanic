"use client";

import { useState } from "react";
import { X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { createBooking } from "@/services/api";
import type { BookingData, BookingErrors, DiagnosisData } from "@/types/chat";

interface Props {
  conversationId: number;
  diagnosis: DiagnosisData | null;
  onClose: () => void;
}

interface FormState {
  customer_name: string;
  customer_contact: string;
  car_model: string;
  issue_summary: string;
  service: string;
}

type SubmitState = "idle" | "loading" | "success" | "error";

/**
 * BookingModal — full-screen modal with booking form.
 * Pre-fills issue_summary and service from the Diagnosis if available.
 * Shows field-level errors on 400, confirmation screen on 201.
 */
export function BookingModal({ conversationId, diagnosis, onClose }: Props) {
  const [form, setForm] = useState<FormState>({
    customer_name: "",
    customer_contact: "",
    car_model: "",
    issue_summary: diagnosis?.diagnosis_text ?? "",
    service: diagnosis?.recommendation ?? "",
  });
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [fieldErrors, setFieldErrors] = useState<BookingErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [booking, setBooking] = useState<BookingData | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name as keyof BookingErrors]) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitState("loading");
    setFieldErrors({});
    setGeneralError(null);

    const result = await createBooking({ conversation_id: conversationId, ...form });

    if ("error" in result) {
      setSubmitState("error");
      setGeneralError(result.error);
      if (result.fieldErrors) setFieldErrors(result.fieldErrors);
    } else {
      setBooking(result.data);
      setSubmitState("success");
    }
  };

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden"
        style={{ maxHeight: "90vh", overflowY: "auto" }}
      >
        {/* Close */}
        <button
          onClick={onClose}
          id="booking-modal-close"
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {submitState === "success" && booking ? (
          /* ── Success screen ──────────────────────────────────────────── */
          <div className="flex flex-col items-center gap-5 px-8 py-12 text-center">
            <div className="p-4 rounded-full bg-emerald-500/15">
              <CheckCircle2 className="w-12 h-12 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Booking Confirmed!</h2>
              <p className="text-slate-400 text-sm">
                Your service request has been received. A mechanic will be in touch soon.
              </p>
            </div>
            <div className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-5 py-4 text-left space-y-2">
              <Detail label="Booking ID" value={`#${booking.id}`} />
              <Detail label="Name" value={booking.customer_name} />
              <Detail label="Contact" value={booking.customer_contact} />
              <Detail label="Vehicle" value={booking.car_model} />
              <Detail label="Service" value={booking.service} />
              <Detail label="Status" value={booking.status.toUpperCase()} highlight />
            </div>
            <button
              onClick={onClose}
              className="mt-2 px-8 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition-colors cursor-pointer"
            >
              Done
            </button>
          </div>
        ) : (
          /* ── Form ──────────────────────────────────────────────────────── */
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            <div className="mb-2">
              <h2 className="text-lg font-bold text-white">Book a Mechanic</h2>
              <p className="text-sm text-slate-400 mt-1">
                Fill in your details and we&#39;ll arrange a service appointment.
              </p>
            </div>

            {generalError && (
              <div className="flex items-start gap-2.5 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3">
                <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-300">{generalError}</p>
              </div>
            )}

            <Field
              id="customer_name"
              label="Full Name"
              type="input"
              value={form.customer_name}
              onChange={handleChange}
              placeholder="e.g. Arya Chakraborty"
              error={fieldErrors.customer_name}
              required
            />
            <Field
              id="customer_contact"
              label="Phone / Email"
              type="input"
              value={form.customer_contact}
              onChange={handleChange}
              placeholder="e.g. +91-9876543210"
              error={fieldErrors.customer_contact}
              required
            />
            <Field
              id="car_model"
              label="Vehicle (Make, Model, Year)"
              type="input"
              value={form.car_model}
              onChange={handleChange}
              placeholder="e.g. Toyota Camry 2019"
              error={fieldErrors.car_model}
              required
            />
            <Field
              id="issue_summary"
              label="Issue Summary"
              type="textarea"
              value={form.issue_summary}
              onChange={handleChange}
              placeholder="Describe the problem…"
              error={fieldErrors.issue_summary}
              required
            />
            <Field
              id="service"
              label="Service Required"
              type="input"
              value={form.service}
              onChange={handleChange}
              placeholder="e.g. Full inspection + exhaust repair"
              error={fieldErrors.service}
              required
            />

            <button
              id="booking-submit-btn"
              type="submit"
              disabled={submitState === "loading"}
              className="
                w-full flex items-center justify-center gap-2 mt-2
                px-5 py-3.5 rounded-xl font-semibold text-sm text-white
                bg-gradient-to-r from-blue-600 to-indigo-600
                hover:from-blue-500 hover:to-indigo-500
                disabled:opacity-60 disabled:cursor-not-allowed
                transition-all duration-200 shadow-lg cursor-pointer
              "
            >
              {submitState === "loading" ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Submitting…
                </>
              ) : (
                "Confirm Booking"
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Field({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  error,
  required,
}: {
  id: string;
  label: string;
  type: "input" | "textarea";
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  placeholder?: string;
  error?: string | string[];
  required?: boolean;
}) {
  const errorText = Array.isArray(error) ? error.join(", ") : error;
  const inputClass = `
    w-full px-3.5 py-2.5 rounded-xl text-sm text-white placeholder-slate-500
    bg-slate-800 border transition-colors outline-none
    ${errorText
      ? "border-red-500/60 focus:border-red-400"
      : "border-slate-700 focus:border-blue-500/60"
    }
  `;
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-300">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {type === "textarea" ? (
        <textarea
          id={id}
          name={id}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          rows={3}
          className={`${inputClass} resize-none`}
        />
      ) : (
        <input
          id={id}
          name={id}
          type="text"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          className={inputClass}
        />
      )}
      {errorText && (
        <p className="text-xs text-red-400">{errorText}</p>
      )}
    </div>
  );
}

function Detail({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className={highlight ? "text-emerald-400 font-semibold" : "text-white"}>
        {value}
      </span>
    </div>
  );
}
