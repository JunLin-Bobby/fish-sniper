import { beforeEach, describe, expect, it } from 'vitest'

import type { GenerateBassStrategySuccessResponsePayload } from '../api/fishSniperApiTypes.ts'
import {
  FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY,
  clearStrategyReportSessionStorage,
  readStrategyReportFromSessionStorage,
  saveStrategyReportToSessionStorage,
} from './strategyReportSessionStorage.ts'

const mockSuccessPayload: GenerateBassStrategySuccessResponsePayload = {
  fish_state: 'Fish are slow on bottom.',
  recommendations: [
    { lure_type: 'Jig', lure_color: 'Green', retrieve_technique: 'Slow drag.' },
    { lure_type: 'Crank', lure_color: 'Shad', retrieve_technique: 'Moderate bump.' },
    { lure_type: 'Ned', lure_color: 'Pumpkin', retrieve_technique: 'Dead stick.' },
  ],
  confidence_note: 'Medium confidence.',
  weather_snapshot: {
    temperature_c: 18,
    pressure_hpa: 1013,
    wind_speed_ms: 3,
    condition_code: 'cloudy',
  },
  rag_logs_used: 0,
  referenced_log: null,
  generated_at: '2026-06-07T08:30:00.000Z',
  fallback: false,
}

describe('strategyReportSessionStorage', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('returns null when storage is empty', () => {
    expect(readStrategyReportFromSessionStorage()).toBeNull()
  })

  it('persists and reads a stored report', () => {
    saveStrategyReportToSessionStorage({
      successPayload: mockSuccessPayload,
      requestSummary: {
        region: 'Taichung',
        fishing_location: 'North dock',
        fishing_scene: 'lake',
        target_species: 'Largemouth Bass',
        water_depth_m: 2.5,
      },
    })
    const stored = readStrategyReportFromSessionStorage()
    expect(stored?.successPayload.fish_state).toBe('Fish are slow on bottom.')
    expect(stored?.requestSummary.region).toBe('Taichung')
    expect(sessionStorage.getItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY)).toBeTruthy()
  })

  it('replaces the previous report on a second save', () => {
    saveStrategyReportToSessionStorage({
      successPayload: mockSuccessPayload,
      requestSummary: {
        region: 'A',
        fishing_location: 'Spot A',
        fishing_scene: 'lake',
        target_species: 'Largemouth Bass',
        water_depth_m: 1,
      },
    })
    saveStrategyReportToSessionStorage({
      successPayload: { ...mockSuccessPayload, fish_state: 'Updated fish state.' },
      requestSummary: {
        region: 'B',
        fishing_location: 'Spot B',
        fishing_scene: 'river',
        target_species: 'Smallmouth Bass',
        water_depth_m: 2,
      },
    })
    const stored = readStrategyReportFromSessionStorage()
    expect(stored?.successPayload.fish_state).toBe('Updated fish state.')
    expect(stored?.requestSummary.region).toBe('B')
  })

  it('clear removes the stored report', () => {
    saveStrategyReportToSessionStorage({
      successPayload: mockSuccessPayload,
      requestSummary: {
        region: 'Taichung',
        fishing_location: 'North dock',
        fishing_scene: 'lake',
        target_species: 'Largemouth Bass',
        water_depth_m: 2.5,
      },
    })
    clearStrategyReportSessionStorage()
    expect(readStrategyReportFromSessionStorage()).toBeNull()
  })

  it('returns null for corrupt JSON', () => {
    sessionStorage.setItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY, '{not-json')
    expect(readStrategyReportFromSessionStorage()).toBeNull()
  })
})
