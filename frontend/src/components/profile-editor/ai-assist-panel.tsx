"use client";

/**
 * AI Assist panel (Block "AI-feature UI"): a front door to the previously
 * backend-only AI engine (Block 14) — bio drafting, free-text extraction,
 * and profile quality analysis. "Use this" buttons save the generated text
 * straight into the profile's narratives section (via the normal section-save
 * endpoint) rather than calling the backend's `apply` endpoint, since that
 * endpoint only validates readiness and does not merge fields itself.
 */

import { useState } from "react";

import { TextAreaField } from "@/components/auth-form";
import { SectionCard } from "@/components/profile-editor/section-card";
import {
  useCreateBioDraft,
  useCreateExtractionDraft,
  useCreateQualityAnalysis,
} from "@/lib/ai";
import { authErrorMessage } from "@/lib/auth";
import { useSectionSave } from "@/lib/sections";

const TONES = ["genuine", "warm", "confident", "playful", "formal"];

function AiButton({
  busy,
  onClick,
  children,
}: {
  busy: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className="bg-gradient-brand cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-50"
    >
      {busy ? "Thinking…" : children}
    </button>
  );
}

function UseThisButton({ busy, onClick }: { busy: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className="cursor-pointer rounded-full border border-glass-line px-4 py-1.5 text-[12.5px] font-semibold text-ink-soft transition-colors hover:border-primary hover:text-ink disabled:opacity-50"
    >
      {busy ? "Saving…" : "Use this ✓"}
    </button>
  );
}

function BioDraftCard({ profileId }: { profileId: string }) {
  const [tone, setTone] = useState("genuine");
  const draft = useCreateBioDraft(profileId);
  const save = useSectionSave(profileId, "/narratives");
  const bio = draft.data?.result?.bio ?? null;

  return (
    <SectionCard
      title="Bio draft"
      description="Generate a starting-point bio in the tone you pick — review and use it, or regenerate."
      error={draft.error}
    >
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-[13px] font-medium text-ink-soft">
          Tone
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="mt-1.5 block rounded-lg border border-glass-line bg-[var(--bg-a)] px-3.5 py-2 text-[13.5px] text-ink outline-none focus:border-primary"
          >
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <AiButton busy={draft.isPending} onClick={() => draft.mutate(tone)}>
          Generate bio draft
        </AiButton>
      </div>
      {bio && (
        <div className="glass rounded-xl p-4">
          <p className="text-[13.5px] leading-relaxed whitespace-pre-line">{bio}</p>
          <div className="mt-3 flex items-center gap-3">
            <UseThisButton busy={save.isPending} onClick={() => save.mutate({ bio })} />
            {save.saved && (
              <span className="text-[12.5px] font-semibold text-ink-soft">Saved to About ✓</span>
            )}
          </div>
          {save.error != null && (
            <p role="alert" className="mt-2 text-[12.5px] text-accent">
              {authErrorMessage(save.error)}
            </p>
          )}
        </div>
      )}
    </SectionCard>
  );
}

function ExtractionDraftCard({ profileId }: { profileId: string }) {
  const [text, setText] = useState("");
  const draft = useCreateExtractionDraft(profileId);
  const save = useSectionSave(profileId, "/narratives");
  const headline = draft.data?.result?.fields?.headline ?? null;

  return (
    <SectionCard
      title="Headline from free text"
      description="Paste a paragraph about yourself and get a suggested headline."
      error={draft.error}
    >
      <TextAreaField
        label="Free text"
        name="text"
        maxLength={5000}
        placeholder="e.g. I'm a software engineer based in Toronto who loves hiking and cooking…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <AiButton busy={draft.isPending || !text.trim()} onClick={() => draft.mutate(text)}>
        Suggest a headline
      </AiButton>
      {headline && (
        <div className="glass mt-4 rounded-xl p-4">
          <p className="text-[13.5px] font-medium">{headline}</p>
          <div className="mt-3 flex items-center gap-3">
            <UseThisButton busy={save.isPending} onClick={() => save.mutate({ headline })} />
            {save.saved && (
              <span className="text-[12.5px] font-semibold text-ink-soft">Saved to About ✓</span>
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
}

function QualityAnalysisCard({ profileId }: { profileId: string }) {
  const analysis = useCreateQualityAnalysis(profileId);
  const result = analysis.data?.result ?? null;

  return (
    <SectionCard
      title="Profile quality analysis"
      description="A quick AI read on how complete and compelling your profile looks."
      error={analysis.error}
    >
      <AiButton busy={analysis.isPending} onClick={() => analysis.mutate()}>
        Analyze my profile
      </AiButton>
      {result && (
        <div className="glass mt-4 rounded-xl p-4">
          <div className="mb-3 flex items-center gap-3">
            <span className="bg-gradient-brand grid size-12 place-items-center rounded-full text-[15px] font-bold text-on-primary">
              {result.score}
            </span>
            <span className="text-[13px] text-ink-soft">out of 100</span>
          </div>
          {result.suggestions?.length > 0 && (
            <ul className="list-inside list-disc space-y-1 text-[13px] text-ink-soft">
              {result.suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </SectionCard>
  );
}

export function AiAssistPanel({ profileId }: { profileId: string }) {
  return (
    <div className="space-y-5">
      <BioDraftCard profileId={profileId} />
      <ExtractionDraftCard profileId={profileId} />
      <QualityAnalysisCard profileId={profileId} />
    </div>
  );
}
