import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export function PrivacyLink() {
  const { i18n } = useTranslation()
  return <Link to="/privacy" className="text-sm text-muted-foreground hover:text-primary hover:underline">
    {i18n.language.startsWith('hi') ? 'गोपनीयता नीति' : 'Privacy policy'}
  </Link>
}
