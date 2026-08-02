"use client";

/**
 * Profile onboarding wizard (catalog §5).
 *
 * "Managed by" is a simple field on the first step (best practice for
 * matrimony platforms — shown on the profile as "managed by family/candidate")
 * rather than an upfront fork. The profile is created when Basics is saved;
 * every later step saves through the real section endpoints, so leaving
 * early keeps a resumable draft.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormError, Field, SelectField, TextAreaField } from "@/components/auth-form";
import { ChipSelect } from "@/components/chip-select";
import { api } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/lib/auth";
import { useActingProfile } from "@/lib/profiles";
import {
  useCommunities,
  useInterests,
  useLanguages,
  useReligiousPractices,
} from "@/lib/reference";

const STEPS = ["Basics", "About", "Lifestyle", "Community", "Publish"] as const;

const GENDERS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];
const MARITAL_STATUSES = [
  { value: "never_married", label: "Never married" },
  { value: "divorced", label: "Divorced" },
  { value: "widowed", label: "Widowed" },
  { value: "annulled", label: "Annulled" },
];
const DIETS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "eggetarian", label: "Eggetarian" },
  { value: "non_vegetarian", label: "Non-vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "other", label: "Other" },
];
const HABITS = [
  { value: "no", label: "No" },
  { value: "occasionally", label: "Occasionally" },
  { value: "yes", label: "Yes" },
];

function StepDots({ current }: { current: number }) {
  return (
    <ol className="mb-7 flex flex-wrap items-center gap-2" aria-label="Progress">
      {STEPS.map((name, i) => (
        <li
          key={name}
          aria-current={i === current ? "step" : undefined}
          className={`rounded-full px-3.5 py-1.5 text-[12px] font-medium ${
            i < current
              ? "bg-primary-soft text-ink"
              : i === current
                ? "bg-primary font-semibold text-on-primary"
                : "border border-glass-line text-ink-soft"
          }`}
        >
          {i + 1}. {name}
        </li>
      ))}
    </ol>
  );
}

function WizardNav({
  onBack,
  nextLabel = "Save & continue",
  busy,
}: {
  onBack?: () => void;
  nextLabel?: string;
  busy: boolean;
}) {
  return (
    <div className="mt-2 flex items-center justify-between">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="glass cursor-pointer rounded-full px-5 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-px"
        >
          Back
        </button>
      ) : (
        <span />
      )}
      <button
        type="submit"
        disabled={busy}
        className="bg-gradient-brand cursor-pointer rounded-full px-7 py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-60 disabled:hover:translate-y-0"
      >
        {busy ? "Saving…" : nextLabel}
      </button>
    </div>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const { account } = useAuth();
  const { profiles, refresh, setActingProfileId } = useActingProfile();
  const [step, setStep] = useState(0);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const communities = useCommunities();
  const practices = useReligiousPractices();
  const languages = useLanguages();
  const interests = useInterests();

  const [selCommunities, setSelCommunities] = useState<string[]>([]);
  const [selPractices, setSelPractices] = useState<string[]>([]);
  const [selLanguages, setSelLanguages] = useState<string[]>([]);
  const [selInterests, setSelInterests] = useState<string[]>([]);

  const existingDraft = profiles.find((p) => p.status === "draft");
  const resuming = profileId != null && profileId === existingDraft?.id;

  async function run(action: () => Promise<void>) {
    setError(null);
    setBusy(true);
    try {
      await action();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  // --- Step 0: basics (creates the profile on first save) ---
  function basicsSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    run(async () => {
      let id = profileId;
      if (!id) {
        const managedBy = String(data.get("managed_by") ?? "candidate");
        const created = await api.post<{ id: string }>("/v1/profiles", {
          relationship: managedBy === "family" ? "other" : "self",
        });
        id = created.id;
        setProfileId(id);
        await refresh();
        setActingProfileId(id);
      }
      const body: Record<string, unknown> = {};
      for (const [key, value] of data.entries()) {
        if (key === "managed_by") continue;
        if (typeof value === "string" && value.trim() !== "") body[key] = value.trim();
      }
      await api.patch(`/v1/profiles/${id}/personal-details`, body);
      setStep(1);
    });
  }

  // --- Steps 1-2: PATCH single-resource sections ---
  function sectionSubmit(path: string) {
    return (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      const data = new FormData(e.currentTarget);
      run(async () => {
        const body: Record<string, unknown> = {};
        for (const [key, value] of data.entries()) {
          if (typeof value === "string" && value.trim() !== "") body[key] = value.trim();
        }
        await api.patch(`/v1/profiles/${profileId}${path}`, body);
        setStep((s) => s + 1);
      });
    };
  }

  // --- Step 3: replace-set sections ---
  function setsSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    run(async () => {
      await api.put(`/v1/profiles/${profileId}/communities`, { values: selCommunities });
      await api.put(`/v1/profiles/${profileId}/religious-practices`, { values: selPractices });
      await api.put(`/v1/profiles/${profileId}/languages`, { values: selLanguages });
      await api.put(`/v1/profiles/${profileId}/interests`, { values: selInterests });
      setStep(4);
    });
  }

  // --- Step 4: submit + publish ---
  async function submitAndPublish(publish: boolean) {
    await run(async () => {
      await api.post(`/v1/profiles/${profileId}/submit`);
      if (publish) await api.post(`/v1/profiles/${profileId}/publish`);
      await refresh();
      router.push("/app");
    });
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 font-display text-[26px] font-bold tracking-tight">
        Create a profile
      </h1>
      <p className="mb-6 text-sm text-ink-soft">
        Progress is saved at every step — you can leave and pick up later.
      </p>
      <StepDots current={step} />
      <div className="glass rounded-[26px] p-7">
        <FormError message={error} />

        {step === 0 && (
          <form onSubmit={basicsSubmit} noValidate>
            <h2 className="mb-5 font-display text-lg font-semibold">The basics</h2>
            {existingDraft && !profileId && (
              <button
                type="button"
                onClick={() => {
                  setProfileId(existingDraft.id);
                  setActingProfileId(existingDraft.id);
                }}
                className="mb-5 w-full cursor-pointer rounded-full border border-glass-line py-2.5 text-[13.5px] font-semibold text-ink-soft transition-colors hover:border-primary hover:text-ink"
              >
                Continue my existing draft instead
              </button>
            )}
            <SelectField
              label="Profile managed by"
              name="managed_by"
              defaultValue="candidate"
              disabled={resuming}
              hint={
                resuming
                  ? "Fixed for this draft — set when the profile was created."
                  : "Shown on the profile. Parents and relatives can manage a profile on a candidate's behalf, with their consent."
              }
            >
              <option value="candidate">The candidate themselves</option>
              <option value="family">A parent or family member</option>
            </SelectField>
            <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
              <SelectField
                label="Gender"
                name="gender"
                required
                defaultValue={account?.gender ?? ""}
                hint={
                  account?.gender
                    ? "Pre-filled from what you entered at signup — change it if this profile is for someone else."
                    : undefined
                }
              >
                <option value="" disabled>
                  Select…
                </option>
                {GENDERS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </SelectField>
              <Field label="Date of birth" name="date_of_birth" type="date" required />
              <Field
                label="Height (cm)"
                name="height_cm"
                type="number"
                min={100}
                max={250}
                placeholder="170"
              />
              <SelectField label="Marital status" name="marital_status" defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {MARITAL_STATUSES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </SelectField>
              <Field label="Mother tongue" name="mother_tongue" placeholder="Punjabi" />
            </div>
            <p className="mb-4 text-[12.5px] leading-relaxed text-ink-soft">
              Confirming gender personalizes the experience for the candidate —
              until then everyone sees the same neutral look.
            </p>
            <WizardNav busy={busy} />
          </form>
        )}

        {step === 1 && (
          <form onSubmit={sectionSubmit("/narratives")} noValidate>
            <h2 className="mb-5 font-display text-lg font-semibold">About</h2>
            <Field
              label="Headline"
              name="headline"
              maxLength={120}
              placeholder="A short line that captures who you are"
            />
            <TextAreaField
              label="Bio"
              name="bio"
              maxLength={4000}
              placeholder="Background, education, career, what matters to you…"
            />
            <TextAreaField
              label="Partner expectations"
              name="partner_expectations"
              maxLength={4000}
              placeholder="What you're hoping to find in a partner and their family…"
            />
            <TextAreaField
              label="Family narrative"
              name="family_narrative"
              maxLength={4000}
              placeholder="A little about your family…"
            />
            <WizardNav onBack={() => setStep(0)} busy={busy} />
          </form>
        )}

        {step === 2 && (
          <form onSubmit={sectionSubmit("/lifestyle")} noValidate>
            <h2 className="mb-5 font-display text-lg font-semibold">Lifestyle</h2>
            <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-3">
              <SelectField label="Diet" name="diet" defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {DIETS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </SelectField>
              <SelectField label="Smoking" name="smoking" defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {HABITS.map((h) => (
                  <option key={h.value} value={h.value}>
                    {h.label}
                  </option>
                ))}
              </SelectField>
              <SelectField label="Alcohol" name="alcohol" defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {HABITS.map((h) => (
                  <option key={h.value} value={h.value}>
                    {h.label}
                  </option>
                ))}
              </SelectField>
            </div>
            <TextAreaField
              label="Values & outlook"
              name="values"
              maxLength={1000}
              placeholder="Traditions, faith, and values that shape your life…"
            />
            <WizardNav onBack={() => setStep(1)} busy={busy} />
          </form>
        )}

        {step === 3 && (
          <form onSubmit={setsSubmit} noValidate>
            <h2 className="mb-5 font-display text-lg font-semibold">Community & languages</h2>
            <ChipSelect
              label="Community"
              options={(communities.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
              selected={selCommunities}
              onChange={setSelCommunities}
              hint="Used by discovery filters — pick at least one."
            />
            <ChipSelect
              label="Religious practice"
              options={(practices.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
              selected={selPractices}
              onChange={setSelPractices}
            />
            <ChipSelect
              label="Languages"
              options={(languages.data ?? []).map((o) => ({ value: o.code, label: o.name }))}
              selected={selLanguages}
              onChange={setSelLanguages}
            />
            <ChipSelect
              label="Interests"
              options={(interests.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
              selected={selInterests}
              onChange={setSelInterests}
            />
            <WizardNav onBack={() => setStep(2)} busy={busy} />
          </form>
        )}

        {step === 4 && (
          <div>
            <h2 className="mb-1 font-display text-lg font-semibold">Ready to go live?</h2>
            <p className="mb-6 text-[13.5px] leading-relaxed text-ink-soft">
              Submitting sends the profile for review; publishing makes it
              visible in discovery. You can pause or edit it any time.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                disabled={busy}
                onClick={() => submitAndPublish(true)}
                className="bg-gradient-brand flex-1 cursor-pointer rounded-full py-2.5 text-sm font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:opacity-60"
              >
                {busy ? "Publishing…" : "Submit & publish now"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => submitAndPublish(false)}
                className="glass flex-1 cursor-pointer rounded-full py-2.5 text-sm font-semibold transition-transform hover:-translate-y-px disabled:opacity-60"
              >
                Submit for review only
              </button>
            </div>
            <button
              type="button"
              onClick={() => setStep(3)}
              className="mt-4 cursor-pointer text-[13px] font-medium text-ink-soft hover:text-ink"
            >
              ← Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
