"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useState } from "react";
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

const MOBILE_NAV_MQ = "(max-width: 920px)";

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function useIsMobileNav() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_NAV_MQ);
    const sync = () => setIsMobile(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  return isMobile;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const navId = useId();
  const isMobileNav = useIsMobileNav();

  const closeNav = useCallback(() => setNavOpen(false), []);

  useEffect(() => {
    closeNav();
  }, [pathname, closeNav]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeNav();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [closeNav]);

  useEffect(() => {
    if (!navOpen) return;
    const mq = window.matchMedia(MOBILE_NAV_MQ);
    const onChange = () => {
      if (!mq.matches) closeNav();
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [navOpen, closeNav]);

  useEffect(() => {
    if (!navOpen) return;
    const mq = window.matchMedia(MOBILE_NAV_MQ);
    if (!mq.matches) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [navOpen]);

  const current = navigation.find((item) => item.href === pathname);
  const pageTitle = current?.label ?? "Overview";

  return (
    <div className="app-frame">
      <header className="mobile-header">
        <button
          type="button"
          className="mobile-menu-btn"
          aria-expanded={navOpen}
          aria-controls={navId}
          onClick={() => setNavOpen((o) => !o)}
        >
          <MenuIcon />
          <span className="sr-only">{navOpen ? "Close menu" : "Open menu"}</span>
        </button>
        <div className="mobile-header-titles">
          <p className="eyebrow mobile-header-eyebrow">InfluencerPy</p>
          <p className="mobile-header-title">{pageTitle}</p>
        </div>
        <span className="mobile-header-spacer" aria-hidden />
      </header>

      {navOpen ? (
        <button
          type="button"
          className="drawer-backdrop"
          aria-label="Close menu"
          onClick={closeNav}
        />
      ) : null}

      <aside
        className={`sidebar ${navOpen ? "nav-drawer-open" : ""}`}
        id={navId}
        aria-hidden={isMobileNav && !navOpen ? true : undefined}
        inert={isMobileNav && !navOpen ? true : undefined}
      >
        <div className="sidebar-brand">
          <button
            type="button"
            className="sidebar-drawer-close"
            aria-label="Close menu"
            onClick={closeNav}
          >
            <CloseIcon />
          </button>
          <div className="sidebar-brand-main">
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
                onClick={closeNav}
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
        <div className="content-area">{children}</div>
      </div>
    </div>
  );
}
