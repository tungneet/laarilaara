import Link from "next/link";

import { AuthNavSlot } from "@/components/auth-nav";

export function SiteNav() {
  return (
    <nav className="flex items-center justify-between py-5">
      <Link
        href="/"
        className="font-display text-[22px] font-bold tracking-tight"
      >
        <span className="brand-laari">Laari</span><span className="brand-laara">Laara</span>
      </Link>
      <div className="flex items-center gap-3">
        <AuthNavSlot />
      </div>
    </nav>
  );
}
