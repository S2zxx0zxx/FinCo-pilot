type FinCoLogoProps = {
  size?: number
  className?: string
}

/** FinCo-Pilot mark: a rising finance path ending in a pilot beacon. */
export function FinCoLogo({ size = 24, className }: FinCoLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      preserveAspectRatio="xMidYMid meet"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M5 24V18.5M11 24V14M17 24V17M23 24V10"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        opacity="0.42"
      />
      <path
        d="M5 18.5L11 13.5L17 17L25.5 7.5"
        stroke="currentColor"
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="25.5" cy="7.5" r="3.1" fill="currentColor" />
      <circle cx="25.5" cy="7.5" r="1.1" fill="white" fillOpacity="0.9" />
    </svg>
  )
}
