import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export function TermsLink() {
  const { i18n } = useTranslation()
  return <Link to="/terms" className="text-sm text-muted-foreground hover:text-primary hover:underline">
    {i18n.language.startsWith('hi') ? 'सेवा की शर्तें' : 'Terms of service'}
  </Link>
}
