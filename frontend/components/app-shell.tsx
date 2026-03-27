"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ActivityIcon,
  ComposeIcon,
  HomeIcon,
  LogsIcon,
  RadarIcon,
  ReviewIcon,
  SettingsIcon,
} from "./icons";

const navigation = [
  { href: "/", label: "Home", detail: "Overview", icon: HomeIcon },
  { href: "/scouts", label: "Flows", detail: "Builder", icon: RadarIcon },
  { href: "/reviews", label: "Reviews", detail: "Approval", icon: ReviewIcon },
  { href: "/activity", label: "History", detail: "Activity", icon: ActivityIcon },
  { href: "/compose", label: "Compose", detail: "Draft", icon: ComposeIcon },
  { href: "/settings", label: "Settings", detail: "Workspace", icon: SettingsIcon },
  { href: "/logs", label: "Logs", detail: "Runtime", icon: LogsIcon },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">
            <svg
              aria-hidden="true"
              className="brand-mark-icon"
              fill="none"
              viewBox="0 0 72 72"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle cx="36" cy="36" r="24" stroke="currentColor" strokeOpacity="0.28" strokeWidth="2.5" />
              <circle cx="36" cy="36" r="12" stroke="currentColor" strokeOpacity="0.55" strokeWidth="2.5" />
              <path d="M36 36 52 25" stroke="currentColor" strokeLinecap="round" strokeWidth="3.2" />
              <circle cx="52" cy="25" r="4.5" fill="currentColor" />
              <path
                d="M16 50C23 44 29 41 36 40C45 39 52 42 58 47"
                stroke="url(#brandTrail)"
                strokeLinecap="round"
                strokeWidth="4"
              />
              <defs>
                <linearGradient id="brandTrail" x1="16" y1="50" x2="58" y2="47" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#37D5FF" />
                  <stop offset="1" stopColor="#FFBB4D" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <p className="eyebrow">InfluencerPy</p>
            <h1>Workflow OS</h1>
          </div>
        </div>

        <p className="sidebar-copy">
          Build flows, review drafts, and run your publishing system from one
          local workspace.
        </p>

        <nav className="sidebar-nav" aria-label="Primary">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                className={`nav-link ${isActive ? "active" : ""}`}
                href={item.href}
                key={item.href}
              >
                <span className="nav-icon-wrap">
                  <Icon className="nav-icon" />
                </span>
                <span className="nav-copy">
                  <span className="nav-detail">{item.detail}</span>
                  <span className="nav-label">{item.label}</span>
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-note">
            <span className="signal-dot" />
            Local workspace
          </div>
          <p>Same local data, same automation engine, redesigned for web-first operation.</p>
        </div>
      </aside>

      <div className="content-frame">
        <header className="topbar">
          <div>
            <p className="eyebrow">Workspace</p>
            <p className="topbar-title">
              {navigation.find((item) => item.href === pathname)?.label ?? "Overview"}
            </p>
          </div>
          <div className="topbar-chip">Automation studio</div>
        </header>

        <div className="content-area">{children}</div>
      </div>
    </div>
  );
}
