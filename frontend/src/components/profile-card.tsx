export interface ProfileCardData {
  initials: string;
  name: string;
  meta: string;
  identityTag: string;
  tags: string[];
  score: number;
  verified: boolean;
  photo?: string;
}

export function ProfileCard({ profile }: { profile: ProfileCardData }) {
  return (
    <div className="overflow-hidden rounded-card border border-glass-line bg-white/5 transition-all duration-200 hover:-translate-y-1 hover:border-primary">
      <div className="relative grid h-[170px] place-items-center overflow-hidden bg-[radial-gradient(circle_at_30%_20%,var(--primary-soft),transparent_60%),radial-gradient(circle_at_75%_80%,var(--accent-soft),transparent_55%)] font-display text-5xl font-bold text-white/20">
        {profile.photo ? (
          <img
            src={profile.photo}
            alt={profile.name}
            className="absolute inset-0 h-full w-full object-cover object-top"
          />
        ) : (
          profile.initials
        )}
        {profile.photo && (
          <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-black/45 to-transparent" />
        )}
        {profile.verified && (
          <span className="glass absolute top-3 left-3 rounded-full px-2.5 py-1 text-[10.5px] font-semibold tracking-wide text-white">
            <span className="text-primary">✓</span> Verified
          </span>
        )}
        <span className="bg-gradient-brand absolute top-3 right-3 rounded-full px-2.5 py-1 font-display text-[13px] font-bold text-on-primary">
          {profile.score}%
        </span>
      </div>
      <div className="p-4">
        <div className="font-display text-[16.5px] font-semibold">
          {profile.name}
        </div>
        <div className="mt-0.5 mb-3 text-[12.5px] text-ink-soft">
          {profile.meta}
        </div>
        <p className="mb-3 border-l-2 border-accent pl-2.5 text-[13px] leading-snug font-medium text-ink">
          {profile.identityTag}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {profile.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-3.5 flex gap-2">
          <button
            type="button"
            className="bg-gradient-brand flex-1 cursor-pointer rounded-full py-2 text-[13px] font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110"
          >
            Express interest
          </button>
          <button
            type="button"
            className="glass cursor-pointer rounded-full px-5 py-2 text-[13px] font-semibold transition-all duration-150 hover:-translate-y-px"
          >
            View
          </button>
        </div>
      </div>
    </div>
  );
}
