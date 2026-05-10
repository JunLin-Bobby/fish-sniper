import {
  getLureSubCategoryNameFromSelection,
  isLureColorNameInCatalog,
  type FishSniperLureColorsFileShape,
  type FishSniperLureTypesFileShape,
} from './fishSniperLureAndColorCatalog.ts'

const FISH_SNIPER_LOG_TARGET_SPECIES_ALLOWED = ['Largemouth Bass', 'Smallmouth Bass'] as const

function isFishSniperLogTargetSpeciesFormValue(value: string): boolean {
  return (FISH_SNIPER_LOG_TARGET_SPECIES_ALLOWED as readonly string[]).includes(value.trim())
}

export type FishSniperMyLogFormFieldErrorKey =
  | 'date'
  | 'fishing_location'
  | 'target_species'
  | 'water_depth_m'
  | 'lure_type'
  | 'lure_color'
  | 'retrieve_speed'
  | 'caught_count'
  | 'weight_lb'
  | 'length_cm'
  | 'temperature_c'
  | 'wind_speed_ms'
  | 'pressure_hpa'

export type FishSniperMyLogFormValidationInput = {
  logDateValue: string
  fishingLocation: string
  targetSpecies: string
  waterDepthMetersText: string
  lureCategoryId: number | null
  lureSubCategoryId: number | null
  lureTypesCatalog: FishSniperLureTypesFileShape
  lureColorName: string
  lureColorsCatalog: FishSniperLureColorsFileShape
  retrieveSpeed: string
  caughtCountText: string
  weightLbText: string
  lengthCmText: string
  manualTemperatureText: string
  manualWindText: string
  manualPressureText: string
}

const ISO_DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/

function isValidIsoCalendarDate(value: string): boolean {
  if (!ISO_DATE_ONLY_REGEX.test(value)) {
    return false
  }
  const parsed = Date.parse(`${value}T00:00:00.000Z`)
  if (Number.isNaN(parsed)) {
    return false
  }
  const roundTrip = new Date(parsed).toISOString().slice(0, 10)
  return roundTrip === value
}

export function validateFishSniperMyLogForm(
  input: FishSniperMyLogFormValidationInput,
): Partial<Record<FishSniperMyLogFormFieldErrorKey, string>> {
  const fieldErrors: Partial<Record<FishSniperMyLogFormFieldErrorKey, string>> = {}

  if (input.logDateValue.trim().length === 0) {
    fieldErrors.date = 'Select a fishing date.'
  } else if (!isValidIsoCalendarDate(input.logDateValue.trim())) {
    fieldErrors.date = 'Select a valid fishing date.'
  }

  if (input.fishingLocation.trim().length === 0) {
    fieldErrors.fishing_location = 'Enter a fishing location.'
  }

  if (!isFishSniperLogTargetSpeciesFormValue(input.targetSpecies)) {
    fieldErrors.target_species = 'Select Largemouth Bass or Smallmouth Bass.'
  }

  const parsedWaterDepthMeters = Number.parseFloat(input.waterDepthMetersText)
  if (!Number.isFinite(parsedWaterDepthMeters) || parsedWaterDepthMeters < 0) {
    fieldErrors.water_depth_m = 'Enter a valid water depth (m) — zero or greater.'
  }

  if (input.lureCategoryId === null || input.lureSubCategoryId === null) {
    fieldErrors.lure_type = 'Select a lure category and subtype.'
  } else {
    const resolvedLureSubCategoryName = getLureSubCategoryNameFromSelection(
      input.lureTypesCatalog,
      input.lureCategoryId,
      input.lureSubCategoryId,
    )
    if (!resolvedLureSubCategoryName) {
      fieldErrors.lure_type = 'Select a lure category and subtype.'
    }
  }

  if (!isLureColorNameInCatalog(input.lureColorsCatalog, input.lureColorName)) {
    fieldErrors.lure_color = 'Select a lure color from the list.'
  }

  if (input.retrieveSpeed.trim().length === 0) {
    fieldErrors.retrieve_speed = 'Enter a retrieve speed or style.'
  }

  const caughtCountTrimmed = input.caughtCountText.trim()
  if (!/^\d+$/.test(caughtCountTrimmed)) {
    fieldErrors.caught_count = 'Enter a whole number of fish caught (0 or more).'
  } else {
    const parsedCaughtCount = Number.parseInt(caughtCountTrimmed, 10)
    if (parsedCaughtCount < 0) {
      fieldErrors.caught_count = 'Enter a whole number of fish caught (0 or more).'
    }
  }

  if (input.weightLbText.trim().length > 0) {
    const parsedWeightLb = Number.parseFloat(input.weightLbText)
    if (!Number.isFinite(parsedWeightLb) || parsedWeightLb < 0) {
      fieldErrors.weight_lb = 'Enter a valid weight (lb) or leave blank.'
    }
  }

  if (input.lengthCmText.trim().length > 0) {
    const parsedLengthCm = Number.parseFloat(input.lengthCmText)
    if (!Number.isFinite(parsedLengthCm) || parsedLengthCm < 0) {
      fieldErrors.length_cm = 'Enter a valid length (cm) or leave blank.'
    }
  }

  const parsedManualTemperatureCelsius = Number.parseFloat(input.manualTemperatureText)
  if (!Number.isFinite(parsedManualTemperatureCelsius)) {
    fieldErrors.temperature_c = 'Enter a valid temperature (°C).'
  }

  const parsedManualWindMetersPerSecond = Number.parseFloat(input.manualWindText)
  if (!Number.isFinite(parsedManualWindMetersPerSecond)) {
    fieldErrors.wind_speed_ms = 'Enter a valid wind speed (m/s).'
  }

  const parsedManualPressureHectopascals = Number.parseInt(input.manualPressureText, 10)
  if (!Number.isFinite(parsedManualPressureHectopascals) || parsedManualPressureHectopascals <= 0) {
    fieldErrors.pressure_hpa = 'Enter a valid pressure (hPa) greater than zero.'
  }

  return fieldErrors
}
