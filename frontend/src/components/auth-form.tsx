"use client";

/** Small shared building blocks for the glass auth forms. */

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass w-full max-w-md rounded-[26px] p-8 shadow-[0_40px_80px_-40px_rgba(0,0,0,0.6)] backdrop-blur-xl">
      <h1 className="font-display text-[26px] font-bold tracking-tight">
        {title}
      </h1>
      <p className="mt-1.5 mb-7 text-sm leading-relaxed text-ink-soft">
        {subtitle}
      </p>
      {children}
    </div>
  );
}

export function Field({
  label,
  hint,
  ...input
}: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="mb-4 block">
      <span className="mb-1.5 block text-[13px] font-medium text-ink-soft">
        {label}
      </span>
      <input
        {...input}
        className="w-full rounded-xl border border-glass-line bg-white/5 px-4 py-2.5 text-[15px] text-ink outline-none transition-colors placeholder:text-ink-soft/50 focus:border-primary"
      />
      {hint && <span className="mt-1.5 block text-xs text-ink-soft">{hint}</span>}
    </label>
  );
}

export function SelectField({
  label,
  hint,
  children,
  ...select
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
} & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="mb-4 block">
      <span className="mb-1.5 block text-[13px] font-medium text-ink-soft">
        {label}
      </span>
      <select
        {...select}
        className="w-full cursor-pointer rounded-xl border border-glass-line bg-white/5 px-4 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-primary [&>option]:bg-slate-800"
      >
        {children}
      </select>
      {hint && <span className="mt-1.5 block text-xs text-ink-soft">{hint}</span>}
    </label>
  );
}

export function TextAreaField({
  label,
  hint,
  ...textarea
}: { label: string; hint?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="mb-4 block">
      <span className="mb-1.5 block text-[13px] font-medium text-ink-soft">
        {label}
      </span>
      <textarea
        {...textarea}
        className="min-h-[96px] w-full resize-y rounded-xl border border-glass-line bg-white/5 px-4 py-2.5 text-[15px] leading-relaxed text-ink outline-none transition-colors placeholder:text-ink-soft/50 focus:border-primary"
      />
      {hint && <span className="mt-1.5 block text-xs text-ink-soft">{hint}</span>}
    </label>
  );
}

export function SubmitButton({
  children,
  busy,
}: {
  children: React.ReactNode;
  busy?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="bg-gradient-brand mt-2 w-full cursor-pointer rounded-full py-2.5 text-[15px] font-semibold text-on-primary transition-all duration-150 hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-60 disabled:hover:translate-y-0"
    >
      {busy ? "Please wait…" : children}
    </button>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="mb-4 rounded-xl border border-accent/40 bg-accent-soft px-4 py-2.5 text-[13.5px]"
    >
      {message}
    </p>
  );
}
