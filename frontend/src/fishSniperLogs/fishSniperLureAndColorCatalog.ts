export type FishSniperLureTypeSubCategory = {
  id: number
  name: string
}

export type FishSniperLureTypeCategory = {
  id: number
  name: string
  subCategories: FishSniperLureTypeSubCategory[]
}

export type FishSniperLureTypesFileShape = {
  lureTypes: FishSniperLureTypeCategory[]
}

export type FishSniperLureColorEntry = {
  id: number
  name: string
}

export type FishSniperLureColorsFileShape = {
  colors: FishSniperLureColorEntry[]
}

export type FishSniperLureSelection = {
  lureCategoryId: number
  lureSubCategoryId: number
}

export function getLureSubCategoryNameFromSelection(
  lureTypesFile: FishSniperLureTypesFileShape,
  lureCategoryId: number,
  lureSubCategoryId: number,
): string | null {
  const category = lureTypesFile.lureTypes.find((entry) => entry.id === lureCategoryId)
  if (!category) {
    return null
  }
  const subCategory = category.subCategories.find((entry) => entry.id === lureSubCategoryId)
  return subCategory ? subCategory.name : null
}

export function findLureSelectionForStoredSubCategoryName(
  lureTypesFile: FishSniperLureTypesFileShape,
  storedLureSubCategoryName: string,
): FishSniperLureSelection | null {
  const trimmed = storedLureSubCategoryName.trim()
  if (trimmed.length === 0) {
    return null
  }
  for (const category of lureTypesFile.lureTypes) {
    const match = category.subCategories.find((sub) => sub.name === trimmed)
    if (match) {
      return { lureCategoryId: category.id, lureSubCategoryId: match.id }
    }
  }
  return null
}

export function isLureColorNameInCatalog(
  lureColorsFile: FishSniperLureColorsFileShape,
  colorName: string,
): boolean {
  const trimmed = colorName.trim()
  if (trimmed.length === 0) {
    return false
  }
  return lureColorsFile.colors.some((entry) => entry.name === trimmed)
}
