interface LogoProps {
  className?: string;
}

export default function Logo({ className = 'h-8 w-8' }: LogoProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Shield body */}
      <path
        d="M16 2L4 8v8c0 7.73 5.12 14.96 12 16 6.88-1.04 12-8.27 12-16V8L16 2z"
        fill="hsl(239 84% 67%)"
        fillOpacity="0.15"
        stroke="hsl(239 84% 67%)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Inner chevron / check mark */}
      <path
        d="M11 16.5l3.5 3.5L21 13"
        stroke="hsl(239 84% 67%)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
