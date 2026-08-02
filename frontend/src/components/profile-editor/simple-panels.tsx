"use client";

import { Field, SelectField, TextAreaField } from "@/components/auth-form";
import { SaveButton, SectionCard } from "@/components/profile-editor/section-card";
import { formBody, useSection, useSectionSave } from "@/lib/sections";

interface PersonalDetails {
  gender: string | null;
  date_of_birth: string | null;
  height_cm: number | null;
  marital_status: string | null;
  mother_tongue: string | null;
}

interface Narratives {
  headline: string | null;
  bio: string | null;
  partner_expectations: string | null;
  family_narrative: string | null;
}

interface Lifestyle {
  diet: string | null;
  smoking: string | null;
  alcohol: string | null;
  fitness_routine: string | null;
  values: string | null;
  life_plans: string | null;
}

interface Visibility {
  discoverable: boolean | null;
  photo_visibility: string | null;
  name_visibility: string | null;
  location_visibility: string | null;
  contact_visibility: string | null;
}

const GENDERS = ["female", "male", "other"];
const MARITAL = ["never_married", "divorced", "widowed", "annulled"];
const DIETS = ["vegetarian", "eggetarian", "non_vegetarian", "vegan", "other"];
const HABITS = ["no", "occasionally", "yes"];
const VISIBILITY_LEVELS = ["public", "connections_only", "managers_only"];

const label = (value: string) =>
  value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

function options(values: string[]) {
  return (
    <>
      <option value="">—</option>
      {values.map((v) => (
        <option key={v} value={v}>
          {label(v)}
        </option>
      ))}
    </>
  );
}

export function BasicsPanel({ profileId }: { profileId: string }) {
  const { data } = useSection<PersonalDetails>(profileId, "/personal-details");
  const save = useSectionSave(profileId, "/personal-details");

  return (
    <SectionCard
      title="Personal details"
      description="Core facts used across discovery and compatibility."
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
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <SelectField label="Gender" name="gender" defaultValue={data?.gender ?? ""}>
            {options(GENDERS)}
          </SelectField>
          <Field
            label="Date of birth"
            name="date_of_birth"
            type="date"
            defaultValue={data?.date_of_birth ?? ""}
          />
          <Field
            label="Height (cm)"
            name="height_cm"
            type="number"
            min={100}
            max={250}
            defaultValue={data?.height_cm ?? ""}
          />
          <SelectField
            label="Marital status"
            name="marital_status"
            defaultValue={data?.marital_status ?? ""}
          >
            {options(MARITAL)}
          </SelectField>
          <Field
            label="Mother tongue"
            name="mother_tongue"
            defaultValue={data?.mother_tongue ?? ""}
            placeholder="Punjabi"
          />
        </div>
        <SaveButton busy={save.isPending} />
      </form>
    </SectionCard>
  );
}

export function AboutPanel({ profileId }: { profileId: string }) {
  const { data } = useSection<Narratives>(profileId, "/narratives");
  const save = useSectionSave(profileId, "/narratives");

  return (
    <SectionCard
      title="About"
      description="The story candidates and families read first."
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
        <Field label="Headline" name="headline" maxLength={120} defaultValue={data?.headline ?? ""} />
        <TextAreaField label="Bio" name="bio" maxLength={4000} defaultValue={data?.bio ?? ""} />
        <TextAreaField
          label="Partner expectations"
          name="partner_expectations"
          maxLength={4000}
          defaultValue={data?.partner_expectations ?? ""}
        />
        <TextAreaField
          label="Family narrative"
          name="family_narrative"
          maxLength={4000}
          defaultValue={data?.family_narrative ?? ""}
        />
        <SaveButton busy={save.isPending} />
      </form>
    </SectionCard>
  );
}

export function LifestylePanel({ profileId }: { profileId: string }) {
  const { data } = useSection<Lifestyle>(profileId, "/lifestyle");
  const save = useSectionSave(profileId, "/lifestyle");

  return (
    <SectionCard
      title="Lifestyle"
      description="Habits and values that matter for compatibility."
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
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-3">
          <SelectField label="Diet" name="diet" defaultValue={data?.diet ?? ""}>
            {options(DIETS)}
          </SelectField>
          <SelectField label="Smoking" name="smoking" defaultValue={data?.smoking ?? ""}>
            {options(HABITS)}
          </SelectField>
          <SelectField label="Alcohol" name="alcohol" defaultValue={data?.alcohol ?? ""}>
            {options(HABITS)}
          </SelectField>
        </div>
        <TextAreaField
          label="Fitness routine"
          name="fitness_routine"
          maxLength={1000}
          defaultValue={data?.fitness_routine ?? ""}
        />
        <TextAreaField
          label="Values & outlook"
          name="values"
          maxLength={1000}
          defaultValue={data?.values ?? ""}
        />
        <TextAreaField
          label="Life plans"
          name="life_plans"
          maxLength={1000}
          defaultValue={data?.life_plans ?? ""}
        />
        <SaveButton busy={save.isPending} />
      </form>
    </SectionCard>
  );
}

export function PrivacyPanel({ profileId }: { profileId: string }) {
  const { data } = useSection<Visibility>(profileId, "/visibility");
  const save = useSectionSave(profileId, "/visibility");

  return (
    <SectionCard
      title="Privacy & visibility"
      description="Control who can see what. Managers always retain access."
      saved={save.saved}
      error={save.error}
    >
      <form
        key={JSON.stringify(data ?? {})}
        onSubmit={(e) => {
          e.preventDefault();
          const data_ = new FormData(e.currentTarget);
          const body = formBody(data_);
          const discoverable = data_.get("discoverable");
          if (discoverable === "true" || discoverable === "false") {
            body.discoverable = discoverable === "true";
          } else {
            delete body.discoverable;
          }
          save.mutate(body);
        }}
        noValidate
      >
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <SelectField
            label="Appear in discovery"
            name="discoverable"
            defaultValue={data?.discoverable == null ? "" : String(data.discoverable)}
          >
            <option value="">—</option>
            <option value="true">Yes — discoverable</option>
            <option value="false">No — hidden</option>
          </SelectField>
          <SelectField
            label="Photos visible to"
            name="photo_visibility"
            defaultValue={data?.photo_visibility ?? ""}
          >
            {options(VISIBILITY_LEVELS)}
          </SelectField>
          <SelectField
            label="Name visible to"
            name="name_visibility"
            defaultValue={data?.name_visibility ?? ""}
          >
            {options(VISIBILITY_LEVELS)}
          </SelectField>
          <SelectField
            label="Location visible to"
            name="location_visibility"
            defaultValue={data?.location_visibility ?? ""}
          >
            {options(VISIBILITY_LEVELS)}
          </SelectField>
          <SelectField
            label="Contact details visible to"
            name="contact_visibility"
            defaultValue={data?.contact_visibility ?? ""}
          >
            {options(VISIBILITY_LEVELS)}
          </SelectField>
        </div>
        <SaveButton busy={save.isPending} />
      </form>
    </SectionCard>
  );
}
