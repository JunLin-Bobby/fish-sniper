import { useTranslation } from 'react-i18next'

// Google 登入操作按鈕，點擊後交由登入頁啟動 OAuth 流程。
export function GoogleSignInButton(props: { disabled?: boolean; onSignIn: () => void | Promise<void> }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      className="w-full cursor-pointer rounded-xl border border-white/20 bg-white py-3.5 text-sm font-bold text-[#010409] transition-colors duration-200 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-55 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
      disabled={props.disabled}
      onClick={() => void props.onSignIn()}
    >
      {t('auth.continueWithGoogle')}
    </button>
  )
}
