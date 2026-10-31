"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Upload" },
  { href: "/questions", label: "Question Bank" },
  { href: "/study-set", label: "Study Set" },
];

export default function NavLinks() {
  const pathname = usePathname();

  return (
    <div className="order-last flex w-full items-center gap-0.5 rounded-full bg-muted p-1 sm:order-none sm:w-auto">
      {LINKS.map((link) => {
        const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`flex-1 whitespace-nowrap rounded-full px-3 py-1 text-center sm:flex-none text-[13px] font-medium tracking-[-0.01em] transition-[background-color,color,box-shadow] duration-150 ease-out ${
              active
                ? "bg-card text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06),0_0_0_1px_var(--border)]"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </div>
  );
}
