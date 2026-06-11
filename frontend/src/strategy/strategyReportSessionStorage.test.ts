import { beforeEach, describe, expect, it } from 'vitest'

import { mockStrategyReportV2SuccessPayload } from './fixtures/mockStrategyReportV2Payload.ts'
import {
  FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY,
  clearStrategyReportSessionStorage,
  readStrategyReportFromSessionStorage,
  saveStrategyReportToSessionStorage,
} from './strategyReportSessionStorage.ts'

describe('strategyReportSessionStorage', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('returns null when storage is empty', () => {
    expect(readStrategyReportFromSessionStorage()).toBeNull()
  })

  it('persists and reads a stored v2 report', () => {
    saveStrategyReportToSessionStorage({
      successPayload: mockStrategyReportV2SuccessPayload,
      requestSummary: {
        region: 'Taichung',
        fishing_location: 'North dock',
        fishing_scene: 'lake',
        target_species: 'Largemouth Bass',
        water_depth_m: 2.5,
      },
    })
    const stored = readStrategyReportFromSessionStorage()
    expect(stored?.successPayload.todays_pattern.headline).toBe('Post-Spawn Largemouth')
    expect(stored?.successPayload.confidence_pct).toBe(82)
    expect(stored?.successPayload.holding_zones).toHaveLength(3)
    expect(stored?.requestSummary.region).toBe('Taichung')
    expect(sessionStorage.getItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY)).toBeTruthy()
  })

  it('replaces the previous report on a second save', () => {
    saveStrategyReportToSessionStorage({
      successPayload: mockStrategyReportV2SuccessPayload,
      requestSummary: {
        region: 'A',
        fishing_location: 'Spot A',
        fishing_scene: 'lake',
        target_species: 'Largemouth Bass',
        water_depth_m: 1,
      },
    })
    saveStrategyReportToSessionStorage({
      successPayload: {
        ...mockStrategyReportV2SuccessPayload,
        fish_state: 'Updated fish state.',
      },
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
      successPayload: mockStrategyReportV2SuccessPayload,
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

  it('returns null for legacy payload missing v2 fields', () => {
    sessionStorage.setItem(
      FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY,
      JSON.stringify({
        version: 1,
        savedAt: '2026-06-07T08:30:00.000Z',
        requestSummary: {
          region: 'Taichung',
          fishing_location: 'North dock',
          fishing_scene: 'lake',
          target_species: 'Largemouth Bass',
          water_depth_m: 2.5,
        },
        successPayload: {
          fish_state: 'Legacy only.',
          confidence_note: 'Old shape.',
          recommendations: [
            { lure_type: 'Jig', lure_color: 'Green', retrieve_technique: 'Slow.' },
            { lure_type: 'Crank', lure_color: 'Shad', retrieve_technique: 'Bump.' },
            { lure_type: 'Ned', lure_color: 'Pumpkin', retrieve_technique: 'Dead.' },
          ],
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
        },
      }),
    )
    expect(readStrategyReportFromSessionStorage()).toBeNull()
  })
})
