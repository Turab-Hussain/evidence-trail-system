export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#1D5C8F" />
      <path d="M10 8v16M10 16h12" stroke="#FFE27A" strokeWidth="3" strokeLinecap="round" />
      <circle cx="22" cy="16" r="3" fill="#FFE27A" />
    </svg>
  );
}
