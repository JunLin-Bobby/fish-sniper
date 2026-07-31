export function TacticalBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-[#010409]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_15%_20%,rgba(61,255,138,0.12),transparent_55%),radial-gradient(ellipse_70%_50%_at_85%_15%,rgba(245,158,11,0.08),transparent_50%),radial-gradient(ellipse_60%_40%_at_70%_90%,rgba(61,255,138,0.06),transparent_45%)]" />
      <svg
        className="absolute inset-0 h-full w-full opacity-[0.14]"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern id="fs-contour-grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path
              d="M0 24h48M24 0v48"
              fill="none"
              stroke="rgba(61,255,138,0.35)"
              strokeWidth="0.5"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#fs-contour-grid)" />
        <path
          d="M-40 180 Q120 120 280 160 T560 140 T820 200 T1100 150"
          fill="none"
          stroke="rgba(61,255,138,0.25)"
          strokeWidth="1"
        />
        <path
          d="M-20 280 Q160 220 340 260 T620 240 T900 300"
          fill="none"
          stroke="rgba(61,255,138,0.18)"
          strokeWidth="1"
        />
        <path
          d="M0 380 Q200 320 400 360 T780 340"
          fill="none"
          stroke="rgba(245,158,11,0.15)"
          strokeWidth="1"
        />
        <path
          d="M200 -20 Q260 120 220 260 T180 520"
          fill="none"
          stroke="rgba(61,255,138,0.12)"
          strokeWidth="1"
        />
      </svg>
      <div className="absolute -right-24 top-1/4 h-[28rem] w-[28rem] rounded-full border border-[#3dff8a]/10 opacity-40 motion-safe:animate-pulse motion-reduce:animate-none" />
      <div className="absolute -right-12 top-[30%] h-[20rem] w-[20rem] rounded-full border border-[#3dff8a]/15 opacity-30" />
      <div className="absolute -right-6 top-[34%] h-[12rem] w-[12rem] rounded-full border border-[#3dff8a]/20 opacity-50" />
    </div>
  )
}
