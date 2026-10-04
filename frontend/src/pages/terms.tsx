import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchTerms } from '@/lib/terms'
import { Button } from '@/components/ui/button'
import { FinCoLogo } from '@/components/finco-logo'

export default function TermsPage() {
  const { i18n } = useTranslation()
  const [language, setLanguage] = useState<'en' | 'hi'>(() => i18n.language.startsWith('hi') ? 'hi' : 'en')
  const hi = language === 'hi'
  const query = useQuery({ queryKey: ['public-terms'], queryFn: fetchTerms, staleTime: 0, gcTime: 0, retry: 1 })
  const terms = query.data
  const absent = hi ? 'इस सेवा के लिए अभी नहीं दिया गया' : 'Not yet provided for this installation'
  useEffect(() => {
    const previous = document.title
    document.title = hi ? 'सेवा की शर्तें | FinCo-Pilot' : 'Terms of service | FinCo-Pilot'
    return () => { document.title = previous }
  }, [hi])

  return <main lang={language} className="min-h-screen bg-background px-4 py-8 text-foreground sm:px-6">
    <div className="mx-auto max-w-4xl space-y-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Link to="/login" className="flex items-center gap-2 font-semibold"><FinCoLogo size={25} />FinCo-Pilot</Link>
        <div className="flex gap-2" aria-label={hi ? 'शर्तों की भाषा' : 'Terms language'}>
          <Button variant="outline" aria-pressed={!hi} onClick={() => setLanguage('en')}>English</Button>
          <Button variant="outline" aria-pressed={hi} onClick={() => setLanguage('hi')}>हिन्दी</Button>
        </div>
      </header>
      <h1 className="text-3xl font-semibold tracking-tight">{hi ? 'सेवा की शर्तें' : 'Terms of service'}</h1>
      {query.isPending && <p role="status">{hi ? 'शर्तें लोड हो रही हैं…' : 'Loading terms…'}</p>}
      {query.isError && <div role="alert" className="space-y-3 rounded-xl border p-5">
        <p>{hi ? 'शर्तें उपलब्ध नहीं हैं। इन्हें प्रकाशित या स्वीकार किया हुआ न मानें।' : 'Terms are unavailable. Do not assume they are published or accepted.'}</p>
        <Button variant="outline" onClick={() => void query.refetch()}>{hi ? 'फिर प्रयास करें' : 'Try again'}</Button>
      </div>}
      {terms && <>
        <section className="space-y-2 rounded-xl border bg-muted/30 p-5">
          <p className="font-medium">{terms.status === 'published' ? (hi ? 'प्रकाशित शर्तें' : 'Published terms') : (hi ? 'मसौदा — प्रकाशन बाकी है' : 'Draft — publication pending')}</p>
          {terms.status !== 'published' && <p className="text-sm leading-6">{hi ? 'संचालक, संपर्क, गोपनीयता और व्यावसायिक निर्णय की वास्तविक जानकारी तथा समीक्षा मिलने तक ये प्रभावी प्रकाशित शर्तें नहीं हैं।' : 'These are not effective published terms until real operator/contact facts, privacy publication and commercial decisions are reviewed.'}</p>}
          <p className="text-xs break-all">{terms.version}</p>
          <p className="text-sm">{hi ? 'समीक्षा' : 'Reviewed'}: {terms.reviewed_on} · {hi ? 'प्रभावी तारीख' : 'Effective date'}: {terms.effective_date ?? (hi ? 'अभी तय नहीं' : 'Not set')}</p>
          <p className="text-sm">{hi ? 'परीक्षण में भुगतान का सत्यापन योजना सक्रिय नहीं करता। वास्तविक पैसे लेना, नियमित शुल्क और स्वचालित धनवापसी इस संस्करण में चालू नहीं हैं।' : 'Test payment verification does not activate a plan. Live money collection, recurring charges and automated refunds are not operational in this build.'}</p>
        </section>
        <section className="space-y-4 rounded-xl border p-5" aria-labelledby="terms-operator">
          <h2 id="terms-operator" className="text-xl font-semibold">{hi ? 'संचालक और शिकायत संपर्क' : 'Operator and grievance contact'}</h2>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            {[[hi ? 'कानूनी नाम' : 'Legal name', terms.operator.legal_name],
              [hi ? 'प्रकार / देश' : 'Type / country', `${terms.operator.entity_type} / ${terms.operator.country_code}`],
              [hi ? 'संपर्क का नाम' : 'Contact name', terms.contact.name],
              [hi ? 'पदनाम' : 'Designation', terms.contact.designation],
              [hi ? 'सार्वजनिक पता' : 'Public address', terms.contact.address],
              [hi ? 'फोन' : 'Phone', terms.contact.phone],
              [hi ? 'वेबसाइट' : 'Website', terms.contact.website]].map(([label, value]) => <div key={label}><dt className="text-muted-foreground">{label}</dt><dd className="mt-1 whitespace-pre-wrap break-words">{value ?? absent}</dd></div>)}
            <div><dt className="text-muted-foreground">{hi ? 'ईमेल' : 'Email'}</dt><dd className="mt-1 break-all">{terms.contact.email ? <a href={`mailto:${encodeURIComponent(terms.contact.email)}`} className="underline">{terms.contact.email}</a> : absent}</dd></div>
          </dl>
        </section>
        <section className="space-y-4 rounded-xl border p-5" aria-labelledby="terms-commercial">
          <h2 id="terms-commercial" className="text-xl font-semibold">{hi ? 'धनवापसी और रद्द करने के निर्णय' : 'Refund and cancellation decisions'}</h2>
          <p className="whitespace-pre-wrap break-words text-sm leading-7">{terms.commercial.refund_policy[language] ?? (hi ? 'धनवापसी की व्यावसायिक शर्तें अभी समीक्षा के लिए बाकी हैं।' : 'Operator refund eligibility/window and handling decisions remain pending review.')}</p>
          <p className="whitespace-pre-wrap break-words text-sm leading-7">{terms.commercial.cancellation_policy[language] ?? (hi ? 'रद्द करने और सेवा अवधि की व्यावसायिक शर्तें अभी समीक्षा के लिए बाकी हैं।' : 'Operator cancellation/service-period decisions remain pending review.')}</p>
          <Link to="/pricing" className="inline-block text-sm underline">{hi ? 'वर्तमान योजना सूची देखें' : 'View current plan catalog'}</Link>
        </section>
        <nav aria-label={hi ? 'शर्तों की विषय सूची' : 'Terms contents'} className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {terms.sections.map(section => <a key={section.id} href={`#${section.id}`} className="underline underline-offset-4">{section.title[language]}</a>)}
        </nav>
        {terms.sections.map(section => <section key={section.id} id={section.id} className="scroll-mt-6 space-y-3 border-t pt-6">
          <h2 className="text-xl font-semibold">{section.title[language]}</h2>
          <p className="whitespace-pre-wrap text-sm leading-7 sm:text-base">{section.body[language]}</p>
        </section>)}
      </>}
      <footer className="flex flex-wrap gap-5 border-t pt-6 text-sm">
        <Link to="/privacy" className="underline">{hi ? 'गोपनीयता नीति' : 'Privacy policy'}</Link>
        <Link to="/support?category=billing_payment" className="underline">{hi ? 'सेवा और भुगतान सहायता' : 'Service and billing help'}</Link>
        <Link to="/login" className="underline">{hi ? 'प्रवेश पृष्ठ पर जाएँ' : 'Return to sign in'}</Link>
      </footer>
    </div>
  </main>
}
