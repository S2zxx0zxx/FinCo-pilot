import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchPrivacyPolicy } from '@/lib/privacy-policy'
import { Button } from '@/components/ui/button'
import { FinCoLogo } from '@/components/finco-logo'

export default function PrivacyPage() {
  const { i18n } = useTranslation()
  const [language, setLanguage] = useState<'en' | 'hi'>(() => i18n.language.startsWith('hi') ? 'hi' : 'en')
  const hi = language === 'hi'
  const query = useQuery({ queryKey: ['public-privacy-policy'], queryFn: fetchPrivacyPolicy, staleTime: 0, gcTime: 0, retry: 1 })
  const policy = query.data
  useEffect(() => {
    const previous = document.title
    document.title = hi ? 'गोपनीयता नीति | FinCo-Pilot' : 'Privacy policy | FinCo-Pilot'
    return () => { document.title = previous }
  }, [hi])
  const absent = hi ? 'इस इंस्टॉलेशन के लिए अभी नहीं दिया गया' : 'Not yet provided for this installation'

  return <main lang={language} className="min-h-screen bg-background px-4 py-8 text-foreground sm:px-6">
    <div className="mx-auto max-w-4xl space-y-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Link to="/login" className="flex items-center gap-2 font-semibold"><FinCoLogo size={25} />FinCo-Pilot</Link>
        <div className="flex gap-2" aria-label={hi ? 'नीति की भाषा' : 'Policy language'}>
          <Button variant="outline" aria-pressed={!hi} onClick={() => setLanguage('en')}>English</Button>
          <Button variant="outline" aria-pressed={hi} onClick={() => setLanguage('hi')}>हिन्दी</Button>
        </div>
      </header>
      <h1 className="text-3xl font-semibold tracking-tight">{hi ? 'गोपनीयता नीति' : 'Privacy policy'}</h1>
      {query.isPending && <p role="status">{hi ? 'नीति लोड हो रही है…' : 'Loading privacy notice…'}</p>}
      {query.isError && <div role="alert" className="space-y-3 rounded-xl border p-5">
        <p>{hi ? 'अभी नीति नहीं मिली। इसे प्रकाशित मानकर आगे न बढ़ें।' : 'The notice is unavailable. Do not assume it is published.'}</p>
        <Button variant="outline" onClick={() => void query.refetch()}>{hi ? 'फिर प्रयास करें' : 'Try again'}</Button>
      </div>}
      {policy && <>
        <div className="space-y-2 rounded-xl border bg-muted/30 p-5">
          <p className="font-medium">{policy.status === 'published' ? (hi ? 'प्रकाशित नीति' : 'Published policy') : (hi ? 'ड्राफ्ट — प्रकाशन बाकी है' : 'Draft — publication pending')}</p>
          {policy.status !== 'published' && <p className="text-sm leading-6">{hi ? 'संचालक, संपर्क और deployment की वास्तविक जानकारी तथा समीक्षा पूरी होने तक यह प्रभावी प्रकाशित नीति नहीं है।' : 'This is not an effective published policy until real operator, contact and deployment details are supplied and reviewed.'}</p>}
          <p className="text-xs break-all">{policy.version}</p>
          <p className="text-sm">{hi ? 'समीक्षा' : 'Reviewed'}: {policy.reviewed_on} · {hi ? 'प्रभावी तारीख' : 'Effective date'}: {policy.effective_date ?? (hi ? 'अभी तय नहीं' : 'Not set')}</p>
        </div>
        <section className="space-y-4 rounded-xl border p-5" aria-labelledby="privacy-operator">
          <h2 id="privacy-operator" className="text-xl font-semibold">{hi ? 'संचालक और privacy/grievance संपर्क' : 'Operator and privacy/grievance contact'}</h2>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            {[[hi ? 'संचालक का कानूनी नाम' : 'Operator legal name', policy.operator.legal_name],
              [hi ? 'संचालक का प्रकार / देश' : 'Operator type / country', `${policy.operator.entity_type} / ${policy.operator.country_code}`],
              [hi ? 'संपर्क का नाम' : 'Contact name', policy.contact.name],
              [hi ? 'सार्वजनिक संपर्क पता' : 'Public contact address', policy.contact.address],
              [hi ? 'Infrastructure providers' : 'Infrastructure providers', policy.deployment.providers],
              [hi ? 'Processing locations' : 'Processing locations', policy.deployment.locations]].map(([label, value]) => <div key={label}><dt className="text-muted-foreground">{label}</dt><dd className="mt-1 whitespace-pre-wrap break-words">{value ?? absent}</dd></div>)}
            <div><dt className="text-muted-foreground">{hi ? 'संपर्क ईमेल' : 'Contact email'}</dt><dd className="mt-1 break-all">{policy.contact.email ? <a href={`mailto:${encodeURIComponent(policy.contact.email)}`} className="underline">{policy.contact.email}</a> : absent}</dd></div>
          </dl>
        </section>
        <nav aria-label={hi ? 'नीति की विषय सूची' : 'Policy contents'} className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {policy.sections.map(section => <a key={section.id} href={`#${section.id}`} className="underline underline-offset-4">{section.title[language]}</a>)}
        </nav>
        {policy.sections.map(section => <section key={section.id} id={section.id} className="scroll-mt-6 space-y-3 border-t pt-6">
          <h2 className="text-xl font-semibold">{section.title[language]}</h2>
          <p className="whitespace-pre-wrap text-sm leading-7 sm:text-base">{section.body[language]}</p>
        </section>)}
      </>}
      <footer className="flex flex-wrap gap-5 border-t pt-6 text-sm">
        <Link to="/terms" className="underline">{hi ? 'सेवा की शर्तें' : 'Terms of service'}</Link>
        <Link to="/support?category=privacy_data" className="underline">{hi ? 'Privacy सहायता' : 'Privacy help'}</Link>
        <Link to="/login" className="underline">{hi ? 'साइन इन पर जाएँ' : 'Return to sign in'}</Link>
      </footer>
    </div>
  </main>
}
