"use client";

/** Multi-select chip group used for communities / languages / interests. */

export function ChipSelect({
  label,
  options,
  selected,
  onChange,
  hint,
}: {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (next: string[]) => void;
  hint?: string;
}) {
  function toggle(value: string) {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value],
    );
  }

  return (
    <div className="mb-5">
      <span className="mb-2 block text-[13px] font-medium text-ink-soft">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(opt.value)}
              className={`cursor-pointer rounded-full px-4 py-1.5 text-[13px] transition-all duration-150 ${
                active
                  ? "bg-primary font-semibold text-on-primary"
                  : "border border-glass-line font-medium text-ink-soft hover:border-primary hover:text-ink"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
      {hint && <span className="mt-2 block text-xs text-ink-soft">{hint}</span>}
    </div>
  );
}
