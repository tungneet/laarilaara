export function ComingSoon({ title, note }: { title: string; note: string }) {
  return (
    <div className="glass rounded-[26px] p-10 text-center">
      <h1 className="font-display text-[22px] font-bold tracking-tight">{title}</h1>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-soft">{note}</p>
    </div>
  );
}
