import type { PropsWithChildren } from "react";

type IconProps = {
  className?: string;
};

function Svg({ className, children }: PropsWithChildren<IconProps>) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  );
}

export function HomeIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5.5 9.5V20h13V9.5" />
      <path d="M10 20v-5h4v5" />
    </Svg>
  );
}

export function RadarIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="12" cy="12" r="3.5" />
      <path d="M12 4.5v7l5.5 3" />
    </Svg>
  );
}

export function ReviewIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="m8.5 12 2.2 2.2 4.8-4.9" />
    </Svg>
  );
}

export function ActivityIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M4 14h3l2.2-6 3.4 10 2.1-6H20" />
    </Svg>
  );
}

export function ComposeIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M4 20h4l10-10-4-4L4 16v4Z" />
      <path d="m12.5 7.5 4 4" />
    </Svg>
  );
}

export function SettingsIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a8 8 0 0 0-1.8-1l-.3-2.6h-4l-.3 2.6a8 8 0 0 0-1.8 1l-2.4-1-2 3.5 2 1.5A7 7 0 0 0 5 12c0 .3 0 .7.1 1l-2 1.5 2 3.5 2.4-1a8 8 0 0 0 1.8 1l.3 2.6h4l.3-2.6a8 8 0 0 0 1.8-1l2.4 1 2-3.5-2-1.5c.1-.3.1-.7.1-1Z" />
    </Svg>
  );
}

export function LogsIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M7 7h10" />
      <path d="M7 12h10" />
      <path d="M7 17h6" />
      <rect x="4" y="4" width="16" height="16" rx="3" />
    </Svg>
  );
}

export function SparkIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z" />
    </Svg>
  );
}

export function PlayIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="m8 6 9 6-9 6V6Z" />
    </Svg>
  );
}

export function StopIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <rect x="7" y="7" width="10" height="10" rx="2" />
    </Svg>
  );
}

export function ClockIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </Svg>
  );
}

export function PlusIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </Svg>
  );
}

export function BranchIcon({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M7 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z" />
      <path d="M17 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z" />
      <path d="M17 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z" />
      <path d="M9 8h4a4 4 0 0 1 4 4v4" />
      <path d="M9 8h8" />
    </Svg>
  );
}
