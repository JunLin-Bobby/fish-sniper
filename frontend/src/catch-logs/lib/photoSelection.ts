export const maxPhotoBytes = 20 * 1024 * 1024

// 前端只做快速大小與張數檢查；實際格式、解碼及像素驗證仍由後端執行。
export function validatePhotoSelection(files: Pick<File, 'size'>[]): boolean {
  return files.length <= 2 && files.every((file) => file.size > 0 && file.size <= maxPhotoBytes)
}
