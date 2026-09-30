import { useTranslation } from 'react-i18next'

// 登出操作按鈕，點擊後交由登入狀態 hook 清除 FishSniper token。
export function SignOutButton(props: { onSignOut: () => void }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      className="min-h-[42px] cursor-pointer rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-bold text-slate-100 transition-colors duration-200 hover:border-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
      onClick={props.onSignOut}
    >
      {t('common.signOut')}
    </button>
  )
}
