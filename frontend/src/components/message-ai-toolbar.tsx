"use client";

/**
 * Inline AI toolbar for the message composer: assistant reply drafts, a tone
 * check on the current draft, and translation. All three are thin wrappers
 * around the synchronous AI-artifact endpoints (Block 14 / catalog §10).
 */

import { useState } from "react";

import {
  useCreateAssistantDraft,
  useCreateToneCheck,
  useCreateTranslationDraft,
} from "@/lib/ai";
import { authErrorMessage } from "@/lib/auth";

const INTENTS = [
  { value: "friendly_opener", label: "Friendly opener" },
  { value: "follow_up_question", label: "Follow-up question" },
  { value: "polite_decline", label: "Polite decline" },
  { value: "propose_call", label: "Propose a call" },
];

const LOCALES = [
  { value: "en", label: "English" },
  { value: "pa", label: "Punjabi" },
  { value: "hi", label: "Hindi" },
  { value: "fr", label: "French" },
];

type Tool = null | "assistant" | "tone" | "translate";

function ToolbarButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`cursor-pointer rounded-full px-3.5 py-1.5 text-[12px] font-semibold transition-colors ${
        active
          ? "bg-primary-soft"
          : "border border-glass-line text-ink-soft hover:border-primary hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

export function MessageAiToolbar({
  actingProfileId,
  conversationId,
  draft,
  onUseText,
}: {
  actingProfileId: string;
  conversationId: string;
  draft: string;
  onUseText: (text: string) => void;
}) {
  const [tool, setTool] = useState<Tool>(null);
  const [intent, setIntent] = useState(INTENTS[0].value);
  const [targetLocale, setTargetLocale] = useState(LOCALES[0].value);

  const assistantDraft = useCreateAssistantDraft(actingProfileId);
  const toneCheck = useCreateToneCheck(actingProfileId);
  const translation = useCreateTranslationDraft(actingProfileId);

  function toggle(next: Tool) {
    setTool((current) => (current === next ? null : next));
  }

  return (
    <div className="mb-3">
      <div className="flex flex-wrap gap-2">
        <ToolbarButton active={tool === "assistant"} onClick={() => toggle("assistant")}>
          ✨ Draft a reply
        </ToolbarButton>
        <ToolbarButton active={tool === "tone"} onClick={() => toggle("tone")}>
          🎭 Check tone
        </ToolbarButton>
        <ToolbarButton active={tool === "translate"} onClick={() => toggle("translate")}>
          🌐 Translate
        </ToolbarButton>
      </div>

      {tool === "assistant" && (
        <div className="glass mt-2 rounded-xl p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              className="rounded-lg border border-glass-line bg-[var(--bg-a)] px-3 py-1.5 text-[12.5px] text-ink outline-none focus:border-primary"
            >
              {INTENTS.map((i) => (
                <option key={i.value} value={i.value}>
                  {i.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={assistantDraft.isPending}
              onClick={() => assistantDraft.mutate({ conversationId, intent })}
              className="bg-gradient-brand cursor-pointer rounded-full px-4 py-1.5 text-[12.5px] font-semibold text-on-primary disabled:opacity-50"
            >
              {assistantDraft.isPending ? "Thinking…" : "Generate"}
            </button>
          </div>
          {assistantDraft.error != null && (
            <p className="mt-2 text-[12px] text-accent">{authErrorMessage(assistantDraft.error)}</p>
          )}
          {assistantDraft.data?.result?.draft && (
            <div className="mt-2.5 rounded-lg border border-glass-line p-2.5">
              <p className="text-[13px] leading-relaxed">{assistantDraft.data.result.draft}</p>
              <button
                type="button"
                onClick={() => onUseText(assistantDraft.data!.result!.draft)}
                className="mt-2 cursor-pointer rounded-full border border-glass-line px-3.5 py-1 text-[12px] font-semibold hover:border-primary"
              >
                Use this ✓
              </button>
            </div>
          )}
        </div>
      )}

      {tool === "tone" && (
        <div className="glass mt-2 rounded-xl p-3.5">
          <button
            type="button"
            disabled={!draft.trim() || toneCheck.isPending}
            onClick={() => toneCheck.mutate({ conversationId, text: draft })}
            className="bg-gradient-brand cursor-pointer rounded-full px-4 py-1.5 text-[12.5px] font-semibold text-on-primary disabled:opacity-50"
          >
            {toneCheck.isPending ? "Checking…" : "Check my current draft"}
          </button>
          {!draft.trim() && (
            <p className="mt-2 text-[12px] text-ink-soft">Type a message first.</p>
          )}
          {toneCheck.error != null && (
            <p className="mt-2 text-[12px] text-accent">{authErrorMessage(toneCheck.error)}</p>
          )}
          {toneCheck.data?.result && (
            <div className="mt-2.5 rounded-lg border border-glass-line p-2.5 text-[13px]">
              <p>
                Tone: <span className="font-semibold capitalize">{toneCheck.data.result.tone}</span>
              </p>
              {toneCheck.data.result.suggestions?.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-ink-soft">
                  {toneCheck.data.result.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {tool === "translate" && (
        <div className="glass mt-2 rounded-xl p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={targetLocale}
              onChange={(e) => setTargetLocale(e.target.value)}
              className="rounded-lg border border-glass-line bg-[var(--bg-a)] px-3 py-1.5 text-[12.5px] text-ink outline-none focus:border-primary"
            >
              {LOCALES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!draft.trim() || translation.isPending}
              onClick={() => translation.mutate({ conversationId, targetLocale, text: draft })}
              className="bg-gradient-brand cursor-pointer rounded-full px-4 py-1.5 text-[12.5px] font-semibold text-on-primary disabled:opacity-50"
            >
              {translation.isPending ? "Translating…" : "Translate my draft"}
            </button>
          </div>
          {!draft.trim() && (
            <p className="mt-2 text-[12px] text-ink-soft">Type a message first.</p>
          )}
          {translation.error != null && (
            <p className="mt-2 text-[12px] text-accent">{authErrorMessage(translation.error)}</p>
          )}
          {translation.data?.result?.translated_text && (
            <div className="mt-2.5 rounded-lg border border-glass-line p-2.5">
              <p className="text-[13px] leading-relaxed">{translation.data.result.translated_text}</p>
              <button
                type="button"
                onClick={() => onUseText(translation.data!.result!.translated_text)}
                className="mt-2 cursor-pointer rounded-full border border-glass-line px-3.5 py-1 text-[12px] font-semibold hover:border-primary"
              >
                Use this ✓
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
