import { describe, expect, it } from 'vitest'

import type {
  FishSniperLureColorsFileShape,
  FishSniperLureTypesFileShape,
} from './fishSniperLureAndColorCatalog.ts'
import {
  findLureSelectionForStoredSubCategoryName,
  getLureSubCategoryNameFromSelection,
  isLureColorNameInCatalog,
} from './fishSniperLureAndColorCatalog.ts'
import { validateFishSniperMyLogForm } from './fishSniperMyLogFormValidation.ts'

const minimalLureTypesCatalog: FishSniperLureTypesFileShape = {
  lureTypes: [
    {
      id: 6,
      name: 'Spinnerbaits',
      subCategories: [
        { id: 601, name: 'Double Willow Blades' },
        { id: 602, name: 'Colorado Willow Blades' },
      ],
    },
  ],
}

const minimalLureColorsCatalog: FishSniperLureColorsFileShape = {
  colors: [
    { id: 1, name: 'Chartreuse' },
    { id: 2, name: 'White' },
  ],
}

function buildValidBaselineInput(): Parameters<typeof validateFishSniperMyLogForm>[0] {
  return {
    logDateValue: '2026-05-09',
    fishingLocation: 'North dock',
    targetSpecies: 'Largemouth Bass',
    waterDepthMetersText: '1.5',
    lureCategoryId: 6,
    lureSubCategoryId: 601,
    lureTypesCatalog: minimalLureTypesCatalog,
    lureColorName: 'Chartreuse',
    lureColorsCatalog: minimalLureColorsCatalog,
    retrieveSpeed: 'Slow',
    caughtCountText: '0',
    weightLbText: '',
    lengthCmText: '',
    manualTemperatureText: '18',
    manualWindText: '3',
    manualPressureText: '1013',
  }
}

describe('fishSniperLureAndColorCatalog', () => {
  it('returns the lure subtype display name for a category + subtype selection', () => {
    expect(getLureSubCategoryNameFromSelection(minimalLureTypesCatalog, 6, 601)).toBe('Double Willow Blades')
  })

  it('returns null when the subtype id does not belong to the category', () => {
    expect(getLureSubCategoryNameFromSelection(minimalLureTypesCatalog, 6, 999)).toBeNull()
  })

  it('maps a stored subtype name back to selection ids', () => {
    expect(findLureSelectionForStoredSubCategoryName(minimalLureTypesCatalog, 'Double Willow Blades')).toEqual({
      lureCategoryId: 6,
      lureSubCategoryId: 601,
    })
  })

  it('returns null when the stored subtype name is unknown', () => {
    expect(findLureSelectionForStoredSubCategoryName(minimalLureTypesCatalog, 'Mystery Bait')).toBeNull()
  })

  it('checks lure color names against the catalog', () => {
    expect(isLureColorNameInCatalog(minimalLureColorsCatalog, 'Chartreuse')).toBe(true)
    expect(isLureColorNameInCatalog(minimalLureColorsCatalog, 'Not a color')).toBe(false)
  })
})

describe('validateFishSniperMyLogForm', () => {
  it('returns no field errors for a valid baseline form', () => {
    expect(validateFishSniperMyLogForm(buildValidBaselineInput())).toEqual({})
  })

  it('requires a fishing date', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      logDateValue: '',
    })
    expect(errors.date).toBeTruthy()
  })

  it('rejects invalid calendar dates', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      logDateValue: '2026-02-31',
    })
    expect(errors.date).toBeTruthy()
  })

  it('requires fishing location', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      fishingLocation: '   ',
    })
    expect(errors.fishing_location).toBeTruthy()
  })

  it('requires a valid target species', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      targetSpecies: 'Walleye',
    })
    expect(errors.target_species).toBeTruthy()
  })

  it('requires non-negative finite water depth', () => {
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), waterDepthMetersText: '-1' }).water_depth_m,
    ).toBeTruthy()
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), waterDepthMetersText: 'abc' }).water_depth_m,
    ).toBeTruthy()
  })

  it('requires a resolved lure subtype selection', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      lureCategoryId: null,
      lureSubCategoryId: null,
    })
    expect(errors.lure_type).toBeTruthy()
  })

  it('requires lure color from catalog', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      lureColorName: 'Custom mix',
    })
    expect(errors.lure_color).toBeTruthy()
  })

  it('requires retrieve speed', () => {
    const errors = validateFishSniperMyLogForm({
      ...buildValidBaselineInput(),
      retrieveSpeed: ' ',
    })
    expect(errors.retrieve_speed).toBeTruthy()
  })

  it('requires non-negative integer caught count', () => {
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), caughtCountText: '-1' }).caught_count,
    ).toBeTruthy()
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), caughtCountText: '1.2' }).caught_count,
    ).toBeTruthy()
  })

  it('validates optional weight and length when provided', () => {
    expect(validateFishSniperMyLogForm({ ...buildValidBaselineInput(), weightLbText: '-1' }).weight_lb).toBeTruthy()
    expect(validateFishSniperMyLogForm({ ...buildValidBaselineInput(), lengthCmText: 'x' }).length_cm).toBeTruthy()
  })

  it('validates manual weather numeric fields', () => {
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), manualTemperatureText: 'nope' }).temperature_c,
    ).toBeTruthy()
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), manualWindText: 'nope' }).wind_speed_ms,
    ).toBeTruthy()
    expect(
      validateFishSniperMyLogForm({ ...buildValidBaselineInput(), manualPressureText: '0' }).pressure_hpa,
    ).toBeTruthy()
  })
})
