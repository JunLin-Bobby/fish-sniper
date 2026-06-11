/** Mock data aligned with GenerateBassStrategySuccessResponsePayload + request summary. */
window.FISH_SNIPER_MOCK_REPORT = {
  requestSummary: {
    region: 'Taichung',
    fishing_location: 'Sun Moon Lake embankment',
    fishing_scene: 'lake',
    target_species: 'Largemouth Bass',
    water_depth_m: 2.5,
  },
  successPayload: {
    fish_state:
      'Fish are holding on brush piles in 6–10 ft after the cold front. Active window is late morning once surface temps climb; bottom contact beats reaction baits today.',
    recommendations: [
      {
        lure_type: 'Football Jig',
        lure_color: 'Green pumpkin',
        retrieve_technique: 'Slow drag with 2-second pauses on bottom transitions.',
      },
      {
        lure_type: 'Mid-depth crankbait',
        lure_color: 'Shad pattern',
        retrieve_technique: 'Moderate retrieve, deflect off stumps, pause on contact.',
      },
      {
        lure_type: 'Ned rig',
        lure_color: 'Mushroom head / green pumpkin TRD',
        retrieve_technique: 'Dead-stick hops along dock shade lines.',
      },
    ],
    confidence_note:
      'Medium-high confidence: weather and your Mar 12 log align on slow bottom presentations.',
    weather_snapshot: {
      temperature_c: 18.5,
      pressure_hpa: 1015,
      wind_speed_ms: 3.2,
      condition_code: 'cloudy',
    },
    rag_logs_used: 1,
    referenced_log: {
      log_id: '00000000-0000-4000-8000-000000000001',
      log_date: '2026-03-12',
      fishing_location: 'Sun Moon Lake embankment',
      lure_type: 'Football Jig',
      lure_color: 'Green pumpkin',
      retrieve_speed: 'slow',
      caught_count: 4,
    },
    generated_at: '2026-06-07T08:30:00.000Z',
    fallback: false,
  },
}

window.formatMockGeneratedAt = function formatMockGeneratedAt(isoTimestamp) {
  const parsed = Date.parse(isoTimestamp)
  if (Number.isNaN(parsed)) {
    return isoTimestamp
  }
  return new Date(parsed).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

window.applyRagVisibility = function applyRagVisibility(showRag) {
  document.querySelectorAll('[data-rag-section]').forEach((element) => {
    element.classList.toggle('hidden-rag', !showRag)
  })
  const ragChip = document.querySelector('[data-rag-chip]')
  if (ragChip) {
    ragChip.textContent = showRag ? 'RAG: 1 log' : 'RAG: general'
  }
}

window.readRagQueryParam = function readRagQueryParam() {
  const params = new URLSearchParams(window.location.search)
  return params.get('rag') !== '0'
}
