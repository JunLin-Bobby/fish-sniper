export const fishingMethods = ['lure', 'front_strike', 'bottom', 'hand_pole', 'fly_fishing', 'other'] as const
export type FishingMethod = typeof fishingMethods[number]

export type CatchLogInput = {
  species_name: string
  caught_at: string
  length_cm: number | null
  weight_g: number | null
  fishing_method: FishingMethod | null
  notes: string | null
}

export type CatchLog = CatchLogInput & {
  id: string
  user_id: string
  created_at: string
  updated_at: string
}

export type CatchLogPage = {
  items: CatchLog[]
  limit: number
  offset: number
  has_more: boolean
}

export type PhotoMetadata = {
  captured_at: string | null
  local_captured_at: string | null
  latitude: number | null
  longitude: number | null
}

export type CatchPhoto = {
  id: string
  photo_order: number
  width: number
  height: number
  url: string
  expires_at: string
  metadata: PhotoMetadata
}
