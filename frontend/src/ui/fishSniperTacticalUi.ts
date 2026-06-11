/** Shared FishSniper tactical UI tokens (Mission brief / Strategy page baseline). */

export const fishSniperTacticalInputClassName =
  'w-full rounded-xl border border-white/15 bg-black/50 px-4 py-3.5 text-base text-slate-100 outline-none transition-colors duration-200 placeholder:text-slate-500 focus:border-[#3dff8a]/60 focus:ring-2 focus:ring-[#3dff8a]/20'

export const fishSniperTacticalSelectClassName =
  'w-full cursor-pointer rounded-xl border border-white/15 bg-black/50 px-4 py-3.5 text-base font-medium text-slate-100 outline-none transition-colors duration-200 focus:border-[#3dff8a]/60 focus:ring-2 focus:ring-[#3dff8a]/20'

export const fishSniperTacticalTextareaClassName =
  `${fishSniperTacticalInputClassName} min-h-[88px] resize-y`

export const fishSniperTacticalPanelClassName =
  'w-full rounded-xl border border-white/15 bg-slate-950/55 p-5 backdrop-blur-md'

export const fishSniperTacticalCardClassName =
  'rounded-xl border border-white/10 bg-black/30 p-6 backdrop-blur-md'

export const fishSniperTacticalChipClassName =
  'inline-flex items-center rounded-full border border-white/15 bg-black/50 px-2.5 py-1 text-[11px] font-medium text-slate-300'

export const fishSniperTacticalEyebrowClassName =
  'text-[10px] font-semibold uppercase tracking-[0.28em] text-[#3dff8a]/75'

export const fishSniperTacticalPageTitleClassName =
  'text-2xl font-bold tracking-tight text-slate-50 sm:text-3xl lg:text-4xl'

export const fishSniperTacticalSectionTitleClassName =
  'text-[10px] font-semibold uppercase tracking-[0.18em] text-[#3dff8a]/80'

export const fishSniperTacticalFieldLabelClassName =
  'flex flex-col gap-1.5 text-xs font-medium text-slate-400'

export const fishSniperTacticalBodyTextClassName = 'text-sm leading-relaxed text-slate-300'

export const fishSniperTacticalMutedTextClassName = 'text-sm leading-relaxed text-slate-400'

export const fishSniperTacticalOptionTileBaseClassName =
  'cursor-pointer rounded-xl border px-4 py-3.5 text-center text-sm font-semibold transition-colors duration-200'

export const fishSniperTacticalOptionTileActiveClassName =
  'border-[#3dff8a]/50 bg-[#3dff8a]/10 text-[#5dff9a] shadow-[0_0_20px_rgba(61,255,138,0.12)]'

export const fishSniperTacticalOptionTileIdleClassName =
  'border-white/10 bg-black/30 text-slate-300 hover:border-[#3dff8a]/30 hover:text-slate-100'

export const fishSniperTacticalPrimaryButtonClassName =
  'w-full cursor-pointer rounded-2xl border border-[#3dff8a]/40 bg-[#3dff8a] py-4 text-sm font-bold uppercase tracking-[0.16em] text-[#010409] shadow-[0_0_40px_rgba(61,255,138,0.35)] transition-colors duration-200 hover:bg-[#5dff9a] disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-slate-700 disabled:text-slate-400 disabled:shadow-none sm:py-5 sm:text-base sm:tracking-[0.2em]'

export const fishSniperTacticalSecondaryButtonClassName =
  'cursor-pointer rounded-xl border border-[#3dff8a]/35 bg-[#3dff8a]/10 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-[#5dff9a] transition-colors duration-200 hover:bg-[#3dff8a]/20 disabled:cursor-not-allowed disabled:opacity-50'

export const fishSniperTacticalGhostButtonClassName =
  'cursor-pointer rounded-xl border border-white/15 bg-black/50 px-4 py-2.5 text-sm font-medium text-slate-200 transition-colors duration-200 hover:border-[#3dff8a]/45 hover:text-[#5dff9a] disabled:cursor-not-allowed disabled:opacity-50'

export const fishSniperTacticalDangerButtonClassName =
  'cursor-pointer rounded-xl border border-rose-500/45 bg-rose-950/30 px-4 py-2.5 text-xs font-semibold text-rose-100 transition-colors duration-200 hover:bg-rose-900/40 disabled:cursor-not-allowed disabled:opacity-50'

export const fishSniperTacticalErrorBannerClassName =
  'rounded-xl border border-rose-500/45 bg-rose-950/30 px-4 py-3 text-sm text-rose-100'

export const fishSniperTacticalWarningBannerClassName =
  'rounded-xl border border-amber-500/45 bg-amber-950/30 p-4 text-sm text-amber-100'

export const fishSniperTacticalSuccessTextClassName = 'text-sm text-[#5dff9a]'

export const fishSniperTacticalNavLinkBaseClassName =
  'rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors duration-200 cursor-pointer'

export function fishSniperTacticalPrimaryNavLinkClassName(isActive: boolean): string {
  return `${fishSniperTacticalNavLinkBaseClassName} ${
    isActive
      ? 'bg-[#3dff8a]/15 text-[#5dff9a]'
      : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
  }`
}

export function fishSniperTacticalSettingsNavLinkClassName(isActive: boolean): string {
  return `${fishSniperTacticalNavLinkBaseClassName} inline-flex items-center gap-1.5 border ${
    isActive
      ? 'border-[#3dff8a]/35 bg-black/50 text-slate-100'
      : 'border-transparent text-slate-400 hover:border-white/10 hover:bg-black/40 hover:text-slate-100'
  }`
}

export function fishSniperTacticalSettingsSideNavLinkClassName(
  isActive: boolean,
  isDestructive = false,
): string {
  const base = 'block rounded-lg border-l-2 px-3 py-2 text-sm font-medium transition-colors duration-200'
  if (isDestructive) {
    return `${base} ${
      isActive
        ? 'border-rose-500 bg-rose-950/20 text-rose-200'
        : 'border-transparent text-rose-400 hover:bg-rose-950/10 hover:text-rose-300'
    }`
  }
  return `${base} ${
    isActive
      ? 'border-[#3dff8a] bg-black/40 text-slate-100'
      : 'border-transparent text-slate-400 hover:bg-black/30 hover:text-slate-100'
  }`
}

export const fishSniperTacticalFabClassName =
  'fixed bottom-24 right-4 z-30 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full border border-[#3dff8a]/40 bg-[#3dff8a] text-[#010409] shadow-[0_0_32px_rgba(61,255,138,0.45)] transition-colors duration-200 hover:bg-[#5dff9a] sm:bottom-28'

export const fishSniperTacticalModalPanelClassName =
  `${fishSniperTacticalPanelClassName} max-h-[90vh] w-full max-w-lg overflow-y-auto shadow-2xl`

export const fishSniperTacticalCardHeadingClassName = 'text-lg font-semibold text-slate-100'

export const fishSniperTacticalOtpInputClassName =
  `${fishSniperTacticalInputClassName} py-3 text-center text-lg`

export const fishSniperTacticalAuthCardClassName =
  'w-full max-w-md space-y-6 rounded-2xl border border-white/10 bg-black/40 p-6 backdrop-blur-md sm:p-8'

export const fishSniperTacticalGoogleButtonClassName =
  'w-full cursor-pointer rounded-xl border border-white/20 bg-white py-3.5 text-sm font-semibold text-[#010409] transition-colors duration-200 hover:bg-slate-100'
