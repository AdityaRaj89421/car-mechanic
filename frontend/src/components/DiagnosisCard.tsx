"use client";

import { AlertTriangle, Calendar, CheckCircle, Stethoscope, Wrench } from "lucide-react";
import type { DiagnosisData } from "@/types/chat";

interface Props {
  diagnosis: DiagnosisData;
  onBookNow: () => void;
}

/**
 * DiagnosisCard — shown in the chat when Gemini returns status: "diagnosis_ready".
 * Displays issue, symptoms, recommendation, and a "Book a Mechanic" CTA.
 */
export function DiagnosisCard({ diagnosis, onBookNow }: Props) {
  return (
    <div className="my-4 mx-auto w-full max-w-lg">
      <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-b from-amber-950/60 to-slate-900/80 shadow-xl backdrop-blur-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 bg-amber-500/10 border-b border-amber-500/20">
          <div className="p-2 rounded-xl bg-amber-500/20">
            <Stethoscope className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs font-medium text-amber-400/80 uppercase tracking-wider">
              AI Diagnosis Complete
            </p>
            <h3 className="text-sm font-semibold text-amber-100">
              Vehicle Issue Identified
            </h3>
          </div>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Diagnosis */}
          <Section
            icon={<AlertTriangle className="w-4 h-4 text-red-400" />}
            label="Diagnosis"
            text={diagnosis.diagnosis_text}
            accent="red"
          />

          {/* Symptoms */}
          <Section
            icon={<Wrench className="w-4 h-4 text-blue-400" />}
            label="Observed Symptoms"
            text={diagnosis.symptoms}
            accent="blue"
          />

          {/* Recommendation */}
          <Section
            icon={<CheckCircle className="w-4 h-4 text-emerald-400" />}
            label="Recommendation"
            text={diagnosis.recommendation}
            accent="emerald"
          />
        </div>

        {/* CTA */}
        <div className="px-5 pb-5">
          <button
            id="book-mechanic-btn"
            onClick={onBookNow}
            className="
              w-full flex items-center justify-center gap-2.5
              px-5 py-3.5 rounded-xl font-semibold text-sm
              bg-gradient-to-r from-amber-500 to-orange-500
              hover:from-amber-400 hover:to-orange-400
              text-white shadow-lg shadow-amber-500/20
              transition-all duration-200 hover:scale-[1.02] active:scale-100
              cursor-pointer
            "
          >
            <Calendar className="w-4 h-4" />
            Book a Mechanic
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Helper ────────────────────────────────────────────────────────────────────

function Section({
  icon,
  label,
  text,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  text: string;
  accent: "red" | "blue" | "emerald";
}) {
  const border = {
    red: "border-red-500/30 bg-red-950/30",
    blue: "border-blue-500/30 bg-blue-950/30",
    emerald: "border-emerald-500/30 bg-emerald-950/30",
  }[accent];

  return (
    <div className={`rounded-xl border p-3.5 ${border}`}>
      <div className="flex items-center gap-2 mb-1.5">
        {icon}
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-sm text-slate-200 leading-relaxed">{text}</p>
    </div>
  );
}
