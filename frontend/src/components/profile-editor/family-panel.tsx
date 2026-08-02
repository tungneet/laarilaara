"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Field, SelectField, TextAreaField } from "@/components/auth-form";
import { SaveButton, SectionCard } from "@/components/profile-editor/section-card";
import { api } from "@/lib/api";
import { formBody, triBool, useSection, useSectionSave } from "@/lib/sections";

interface Family {
  family_type: string | null;
  father_living: boolean | null;
  mother_living: boolean | null;
  siblings_count: number | null;
  family_values: string | null;
}

interface FamilyMember {
  id: string;
  relation: string;
  name: string;
  age: number | null;
  occupation: string | null;
  is_married: boolean | null;
}

const FAMILY_TYPES = ["nuclear", "joint", "extended", "other"];
const RELATIONS = ["father", "mother", "brother", "sister", "other"];

const label = (value: string) =>
  value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

export function FamilyPanel({ profileId }: { profileId: string }) {
  const queryClient = useQueryClient();
  const { data } = useSection<Family>(profileId, "/family");
  const save = useSectionSave(profileId, "/family", "put");

  const members = useQuery({
    queryKey: ["family-members", profileId],
    queryFn: () => api.get<FamilyMember[]>(`/v1/profiles/${profileId}/family/members`),
  });

  const addMember = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post(`/v1/profiles/${profileId}/family/members`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["family-members", profileId] }),
  });

  const removeMember = useMutation({
    mutationFn: (memberId: string) =>
      api.delete(`/v1/profiles/${profileId}/family/members/${memberId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["family-members", profileId] }),
  });

  return (
    <div className="space-y-5">
      <SectionCard
        title="Family"
        description="This section is saved as a whole — empty fields are cleared."
        saved={save.saved}
        error={save.error}
      >
        <form
          key={JSON.stringify(data ?? {})}
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            const body = formBody(fd);
            const father = triBool(fd.get("father_living"));
            const mother = triBool(fd.get("mother_living"));
            if (father !== undefined) body.father_living = father;
            else delete body.father_living;
            if (mother !== undefined) body.mother_living = mother;
            else delete body.mother_living;
            save.mutate(body);
          }}
          noValidate
        >
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
            <SelectField label="Family type" name="family_type" defaultValue={data?.family_type ?? ""}>
              <option value="">—</option>
              {FAMILY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {label(t)}
                </option>
              ))}
            </SelectField>
            <Field
              label="Number of siblings"
              name="siblings_count"
              type="number"
              min={0}
              max={50}
              defaultValue={data?.siblings_count ?? ""}
            />
            <SelectField
              label="Father living"
              name="father_living"
              defaultValue={data?.father_living == null ? "" : String(data.father_living)}
            >
              <option value="">—</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </SelectField>
            <SelectField
              label="Mother living"
              name="mother_living"
              defaultValue={data?.mother_living == null ? "" : String(data.mother_living)}
            >
              <option value="">—</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </SelectField>
          </div>
          <TextAreaField
            label="Family values"
            name="family_values"
            maxLength={1000}
            defaultValue={data?.family_values ?? ""}
          />
          <SaveButton busy={save.isPending} />
        </form>
      </SectionCard>

      <SectionCard
        title="Family members"
        description="Introduce the immediate family."
        error={addMember.error ?? removeMember.error}
      >
        <ul className="mb-5 space-y-2">
          {(members.data ?? []).map((m) => (
            <li
              key={m.id}
              className="flex items-center justify-between rounded-xl border border-glass-line bg-white/5 px-4 py-2.5"
            >
              <span className="text-[14px]">
                <span className="font-semibold">{m.name}</span>
                <span className="text-ink-soft">
                  {" "}
                  · {label(m.relation)}
                  {m.age != null && ` · ${m.age}`}
                  {m.occupation && ` · ${m.occupation}`}
                </span>
              </span>
              <button
                type="button"
                onClick={() => removeMember.mutate(m.id)}
                className="cursor-pointer rounded-full border border-glass-line px-3 py-1 text-[12px] font-semibold text-ink-soft transition-colors hover:border-accent hover:text-ink"
              >
                Remove
              </button>
            </li>
          ))}
          {members.data?.length === 0 && (
            <li className="text-[13px] text-ink-soft">No family members added yet.</li>
          )}
        </ul>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            addMember.mutate(formBody(new FormData(form)), {
              onSuccess: () => form.reset(),
            });
          }}
          noValidate
          className="grid grid-cols-1 items-end gap-x-3 sm:grid-cols-[1fr_1fr_100px_auto]"
        >
          <Field label="Name" name="name" required placeholder="Full name" />
          <SelectField label="Relation" name="relation" required defaultValue="">
            <option value="" disabled>
              Select…
            </option>
            {RELATIONS.map((r) => (
              <option key={r} value={r}>
                {label(r)}
              </option>
            ))}
          </SelectField>
          <Field label="Age" name="age" type="number" min={0} max={120} />
          <div className="mb-4">
            <SaveButton busy={addMember.isPending} label="Add" />
          </div>
        </form>
      </SectionCard>
    </div>
  );
}
