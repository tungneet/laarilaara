"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Field, SelectField } from "@/components/auth-form";
import { SaveButton, SectionCard } from "@/components/profile-editor/section-card";
import { api } from "@/lib/api";
import { useEducationLevels, useOccupationCategories } from "@/lib/reference";
import { formBody } from "@/lib/sections";

interface EducationRecord {
  id: string;
  institution: string;
  education_level: string;
  field_of_study: string | null;
  start_year: number | null;
  end_year: number | null;
  is_current: boolean;
}

interface EmploymentRecord {
  id: string;
  employer: string;
  occupation_category: string;
  job_title: string | null;
  start_year: number | null;
  end_year: number | null;
  is_current: boolean;
}

function useRecords<T>(profileId: string, resource: "education" | "employment") {
  const queryClient = useQueryClient();
  const key = [resource, profileId];

  const list = useQuery({
    queryKey: key,
    queryFn: () => api.get<T[]>(`/v1/profiles/${profileId}/${resource}`),
  });
  const add = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post(`/v1/profiles/${profileId}/${resource}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/profiles/${profileId}/${resource}/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  });
  return { list, add, remove };
}

function RecordRow({
  title,
  subtitle,
  onRemove,
}: {
  title: string;
  subtitle: string;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-center justify-between rounded-xl border border-glass-line bg-white/5 px-4 py-2.5">
      <span className="text-[14px]">
        <span className="font-semibold">{title}</span>
        <span className="text-ink-soft"> · {subtitle}</span>
      </span>
      <button
        type="button"
        onClick={onRemove}
        className="cursor-pointer rounded-full border border-glass-line px-3 py-1 text-[12px] font-semibold text-ink-soft transition-colors hover:border-accent hover:text-ink"
      >
        Remove
      </button>
    </li>
  );
}

export function RecordsPanel({ profileId }: { profileId: string }) {
  const education = useRecords<EducationRecord>(profileId, "education");
  const employment = useRecords<EmploymentRecord>(profileId, "employment");
  const levels = useEducationLevels();
  const occupations = useOccupationCategories();

  return (
    <div className="space-y-5">
      <SectionCard
        title="Education"
        description="Degrees and institutions."
        error={education.add.error ?? education.remove.error}
      >
        <ul className="mb-5 space-y-2">
          {(education.list.data ?? []).map((r) => (
            <RecordRow
              key={r.id}
              title={r.institution}
              subtitle={`${levels.data?.find((l) => l.id === r.education_level)?.label ?? r.education_level}${r.field_of_study ? ` · ${r.field_of_study}` : ""}${r.end_year ? ` · ${r.end_year}` : r.is_current ? " · ongoing" : ""}`}
              onRemove={() => education.remove.mutate(r.id)}
            />
          ))}
          {education.list.data?.length === 0 && (
            <li className="text-[13px] text-ink-soft">No education records yet.</li>
          )}
        </ul>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            education.add.mutate(formBody(new FormData(form)), {
              onSuccess: () => form.reset(),
            });
          }}
          noValidate
          className="grid grid-cols-1 items-end gap-x-3 sm:grid-cols-[1fr_1fr_1fr_auto]"
        >
          <Field label="Institution" name="institution" required placeholder="University / school" />
          <SelectField label="Level" name="education_level" required defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {(levels.data ?? []).map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </SelectField>
          <Field label="Field of study" name="field_of_study" placeholder="e.g. Architecture" />
          <div className="mb-4">
            <SaveButton busy={education.add.isPending} label="Add" />
          </div>
        </form>
      </SectionCard>

      <SectionCard
        title="Career"
        description="Current and past work."
        error={employment.add.error ?? employment.remove.error}
      >
        <ul className="mb-5 space-y-2">
          {(employment.list.data ?? []).map((r) => (
            <RecordRow
              key={r.id}
              title={r.employer}
              subtitle={`${r.job_title ?? occupations.data?.find((o) => o.id === r.occupation_category)?.label ?? r.occupation_category}${r.is_current ? " · current" : r.end_year ? ` · until ${r.end_year}` : ""}`}
              onRemove={() => employment.remove.mutate(r.id)}
            />
          ))}
          {employment.list.data?.length === 0 && (
            <li className="text-[13px] text-ink-soft">No work records yet.</li>
          )}
        </ul>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const fd = new FormData(form);
            const body = formBody(fd);
            body.is_current = fd.get("is_current") === "on";
            employment.add.mutate(body, { onSuccess: () => form.reset() });
          }}
          noValidate
          className="grid grid-cols-1 items-end gap-x-3 sm:grid-cols-[1fr_1fr_1fr_auto_auto]"
        >
          <Field label="Employer" name="employer" required placeholder="Company / organisation" />
          <SelectField label="Category" name="occupation_category" required defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {(occupations.data ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </SelectField>
          <Field label="Job title" name="job_title" placeholder="e.g. Senior Architect" />
          <label className="mb-4 flex items-center gap-2 text-[13px] text-ink-soft">
            <input type="checkbox" name="is_current" className="size-4 accent-(--primary)" />
            Current
          </label>
          <div className="mb-4">
            <SaveButton busy={employment.add.isPending} label="Add" />
          </div>
        </form>
      </SectionCard>
    </div>
  );
}
