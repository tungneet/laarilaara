"use client";

import { useState } from "react";

import { Field, TextAreaField } from "@/components/auth-form";
import { ChipSelect } from "@/components/chip-select";
import { SaveButton, SectionCard } from "@/components/profile-editor/section-card";
import {
  useCommunities,
  useCountries,
  useEducationLevels,
  useLanguages,
  useReligiousPractices,
} from "@/lib/reference";
import { formBody, useSection, useSectionSave } from "@/lib/sections";

interface Preferences {
  age_min: number | null;
  age_max: number | null;
  height_min_cm: number | null;
  height_max_cm: number | null;
  notes: string | null;
}

interface SetResponse {
  values: string[];
}

function useSetEditor(profileId: string, path: string) {
  const { data } = useSection<SetResponse>(profileId, path);
  const save = useSectionSave(profileId, path, "put");
  const [values, setValues] = useState<string[]>([]);
  const [syncedData, setSyncedData] = useState(data);

  if (data && data !== syncedData) {
    setSyncedData(data);
    setValues(data.values);
  }

  return { values, setValues, save };
}

export function PreferencesPanel({ profileId }: { profileId: string }) {
  const { data } = useSection<Preferences>(profileId, "/preferences");
  const save = useSectionSave(profileId, "/preferences", "put");

  const countriesRef = useCountries();
  const languagesRef = useLanguages();
  const communitiesRef = useCommunities();
  const practicesRef = useReligiousPractices();
  const levelsRef = useEducationLevels();

  const countries = useSetEditor(profileId, "/preferences/countries");
  const languages = useSetEditor(profileId, "/preferences/languages");
  const communities = useSetEditor(profileId, "/preferences/communities");
  const practices = useSetEditor(profileId, "/preferences/religious-practices");
  const levels = useSetEditor(profileId, "/preferences/education-levels");

  const setsBusy =
    countries.save.isPending ||
    languages.save.isPending ||
    communities.save.isPending ||
    practices.save.isPending ||
    levels.save.isPending;
  const setsSaved =
    countries.save.saved ||
    languages.save.saved ||
    communities.save.saved ||
    practices.save.saved ||
    levels.save.saved;
  const setsError =
    countries.save.error ??
    languages.save.error ??
    communities.save.error ??
    practices.save.error ??
    levels.save.error;

  return (
    <div className="space-y-5">
      <SectionCard
        title="Partner preferences"
        description="Saved as a whole — used to guide discovery and compatibility."
        saved={save.saved}
        error={save.error}
      >
        <form
          key={JSON.stringify(data ?? {})}
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(formBody(new FormData(e.currentTarget)));
          }}
          noValidate
        >
          <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-4">
            <Field label="Age from" name="age_min" type="number" min={18} max={100} defaultValue={data?.age_min ?? ""} />
            <Field label="Age to" name="age_max" type="number" min={18} max={100} defaultValue={data?.age_max ?? ""} />
            <Field label="Height from (cm)" name="height_min_cm" type="number" min={100} max={250} defaultValue={data?.height_min_cm ?? ""} />
            <Field label="Height to (cm)" name="height_max_cm" type="number" min={100} max={250} defaultValue={data?.height_max_cm ?? ""} />
          </div>
          <TextAreaField
            label="Notes"
            name="notes"
            maxLength={1000}
            defaultValue={data?.notes ?? ""}
            placeholder="Anything else that matters…"
          />
          <SaveButton busy={save.isPending} />
        </form>
      </SectionCard>

      <SectionCard
        title="Preferred backgrounds"
        description="Leave a group empty to stay open to all options."
        saved={setsSaved}
        error={setsError}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            countries.save.mutate({ values: countries.values });
            languages.save.mutate({ values: languages.values });
            communities.save.mutate({ values: communities.values });
            practices.save.mutate({ values: practices.values });
            levels.save.mutate({ values: levels.values });
          }}
          noValidate
        >
          <ChipSelect
            label="Countries"
            options={(countriesRef.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
            selected={countries.values}
            onChange={countries.setValues}
          />
          <ChipSelect
            label="Languages"
            options={(languagesRef.data ?? []).map((l) => ({ value: l.code, label: l.name }))}
            selected={languages.values}
            onChange={languages.setValues}
          />
          <ChipSelect
            label="Communities"
            options={(communitiesRef.data ?? []).map((c) => ({ value: c.id, label: c.label }))}
            selected={communities.values}
            onChange={communities.setValues}
          />
          <ChipSelect
            label="Religious practice"
            options={(practicesRef.data ?? []).map((p) => ({ value: p.id, label: p.label }))}
            selected={practices.values}
            onChange={practices.setValues}
          />
          <ChipSelect
            label="Education level"
            options={(levelsRef.data ?? []).map((l) => ({ value: l.id, label: l.label }))}
            selected={levels.values}
            onChange={levels.setValues}
          />
          <SaveButton busy={setsBusy} />
        </form>
      </SectionCard>
    </div>
  );
}
