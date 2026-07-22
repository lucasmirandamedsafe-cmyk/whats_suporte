"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/suporte", label: "💬 Suporte WhatsApp" },
  { href: "/grupos", label: "👥 Grupos" },
];

export function TopNav() {
  const pathname = usePathname();
  return (
    <nav className="border-b border-[#e1e0d9] bg-[#fcfcfb] px-6 py-3 flex gap-6">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`text-sm font-medium transition-colors ${
              active ? "text-[#2a78d6]" : "text-[#52514e] hover:text-[#0b0b0b]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
