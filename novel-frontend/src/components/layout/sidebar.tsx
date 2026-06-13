"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  Palette,
  Lightbulb,
  Wrench,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const navItems = [
  { href: "/", label: "工作台", icon: LayoutDashboard },
  { href: "/projects", label: "项目", icon: BookOpen },
  { href: "/styles", label: "文风", icon: Palette },
  { href: "/ideas", label: "灵感", icon: Lightbulb },
  { href: "/config", label: "配置", icon: Wrench },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside
      className="fixed left-0 top-0 z-[var(--z-sidebar)] flex h-full flex-col border-r"
      style={{
        width: collapsed
          ? "var(--layout-sidebar-collapsed)"
          : "var(--layout-sidebar-expanded)",
        background: "var(--surface-sidebar)",
        borderColor: "var(--border-subtle)",
        transition: "width var(--transition-normal)",
      }}
    >
      {/* Logo */}
      <div
        className="flex h-14 items-center gap-2 overflow-hidden px-4"
        style={{ justifyContent: collapsed ? "center" : "flex-start" }}
      >
        <BookOpen className="size-5 shrink-0" style={{ color: "var(--accent-text)" }} />
        {!collapsed && (
          <span className="font-semibold whitespace-nowrap" style={{ color: "var(--text-primary)" }}>
            Novel Forge
          </span>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <ScrollArea className="flex-1 px-3 py-2">
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const active = isActive(item.href);
            return (
              <div key={item.href} className="relative group">
                <Link
                  href={item.href}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors"
                  style={{
                    justifyContent: collapsed ? "center" : "flex-start",
                    background: active ? "var(--nav-item-active-bg)" : "transparent",
                    color: active ? "var(--nav-item-active-text)" : "var(--nav-item-text)",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "var(--nav-item-hover-bg)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="size-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
                {/* Active indicator — collapsed mode */}
                {active && collapsed && (
                  <div
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 rounded-r-full"
                    style={{ background: "var(--nav-item-active-indicator)" }}
                  />
                )}
                {/* Tooltip — collapsed mode */}
                {collapsed && (
                  <div
                    className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2 py-1 rounded-md text-xs whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity pointer-events-none z-[var(--z-tooltip)]"
                    style={{
                      background: "var(--surface-tooltip)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--border-subtle)",
                      boxShadow: "var(--shadow-dialog)",
                    }}
                  >
                    {item.label}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </ScrollArea>

      <Separator />

      {/* Bottom controls */}
      <div className="flex flex-col gap-1 p-3">
        <ThemeToggle collapsed={collapsed} />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center rounded-md py-2 text-sm transition-colors"
          style={{
            color: "var(--text-tertiary)",
            background: "transparent",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--bg-elevated-hover)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
          }}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <>
              <ChevronLeft className="size-4 mr-1" />
              <span>收起</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
