"use client";

import { useState } from "react";

import { ChipSelect } from "@/components/chip-select";
import { SaveButton, SectionCard } from "@/components/profile-editor/section-card";
import {
  useCommunities,
  useInterests,
  useLanguages,
  useReligiousPractices,
} from "@/lib/reference";
import { useSection, useSectionSave } from "@/lib/sections";

interface SetResponse {
  values: string[];
}

function useSetEditor(profileId: string, path: string) {
  const { data } = useSection<SetResponse>(profileId, path);
  const save = useSectionSave(profileId, path, "put");
  const [values, setValues] = useState<string[]>([]);
  const [syncedData, setSyncedData] = useState(data);

  // Adjust local editable state when freshly-fetched data arrives, without
  // an effect (React's recommended pattern for "state derived from props").
  if (data && data !== syncedData) {
    setSyncedData(data);
    setValues(data.values);
  }

  return { values, setValues, save };
}

export function CommunityPanel({ profileId }: { profileId: string }) {
  const communities = useCommunities();
  const practices = useReligiousPractices();
  const languages = useLanguages();
  const interests = useInterests();

  const com = useSetEditor(profileId, "/communities");
  const pra = useSetEditor(profileId, "/religious-practices");
  const lan = useSetEditor(profileId, "/languages");
  const int = useSetEditor(profileId, "/interests");

  const busy = com.save.isPending || pra.save.isPending || lan.save.isPending || int.save.isPending;
  const saved = com.save.saved || pra.save.saved || lan.save.saved || int.save.saved;
  const error = com.save.error ?? pra.save.error ?? lan.save.error ?? int.save.error;

  return (
    <SectionCard
      title="Community & languages"
      description="Community is used by discovery filters."
      saved={saved}
      error={error}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          com.save.mutate({ values: com.values });
          pra.save.mutate({ values: pra.values });
          lan.save.mutate({ values: lan.values });
          int.save.mutate({ values: int.values });
        }}
        noValidate
      >
        <ChipSelect
          label="Community"
          options={(communities.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
          selected={com.values}
          onChange={com.setValues}
        />
        <ChipSelect
          label="Religious practice"
          options={(practices.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
          selected={pra.values}
          onChange={pra.setValues}
        />
        <ChipSelect
          label="Languages"
          options={(languages.data ?? []).map((o) => ({ value: o.code, label: o.name }))}
          selected={lan.values}
          onChange={lan.setValues}
        />
        <ChipSelect
          label="Interests"
          options={(interests.data ?? []).map((o) => ({ value: o.id, label: o.label }))}
          selected={int.values}
          onChange={int.setValues}
        />
        <SaveButton busy={busy} />
      </form>
    </SectionCard>
  );
}
