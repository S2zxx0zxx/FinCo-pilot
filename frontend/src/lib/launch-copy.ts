import { useTranslation } from 'react-i18next'
import { resolveSupportedLang } from './i18n'

// Launch flows use the same persisted language selection as the rest of the app.
// Keep untranslated locales in English; never present English text as translated.
export const launchHindi: Record<string, string> = {
  'Add and reconcile at least one cash account.': 'कम से कम एक नकद या बैंक खाते को जोड़कर उसका बैलेंस मिलाएँ।',
  'Review balances, scheduled bills, loan repayments and other obligations before using this estimate.': 'इस अनुमान का इस्तेमाल करने से पहले बैलेंस, तय बिल, लोन भुगतान और अन्य देनदारियाँ जाँचें।',
  'An unsupported account type may contain debt; reconcile it before calculating.': 'किसी असमर्थित खाता प्रकार में कर्ज़ हो सकता है; गणना से पहले उसका मिलान ज़रूरी है।',
  'All amounts use your primary currency. This is an estimate, not a bank spending authorization.': 'सभी रकम आपकी मुख्य मुद्रा में हैं। यह अनुमान है, बैंक की खर्च करने की अनुमति नहीं।',
  'Future income, investment assets and unused credit limits are excluded.': 'भविष्य की आय, निवेश और अप्रयुक्त क्रेडिट सीमा इसमें शामिल नहीं हैं।',
  'The full current card debt is reserved, even if its due date is beyond this horizon.': 'कार्ड का पूरा मौजूदा कर्ज़ अलग रखा जाता है, भले ही उसकी देय तारीख इस अवधि के बाद हो।',
  'Pending debits are reserved conservatively; a provider balance may already include them.': 'लंबित डेबिट की रकम सावधानी के लिए अलग रखी जाती है; वे प्रदाता के बैलेंस में पहले से शामिल हो सकते हैं।',
  'Emergency savings, goal contributions and obligations missing from your ledger must be entered separately.': 'आपातकालीन बचत, लक्ष्यों की बचत और खाते में दर्ज न हुई देनदारियाँ अलग से भरें।',
  'Paired transfers between included cash accounts are excluded. Card repayments remain reserved conservatively.': 'शामिल नकद खातों के बीच मिलान किए गए ट्रांसफ़र खर्च नहीं माने जाते। कार्ड भुगतान की रकम सावधानी के लिए अलग रखी जाती है।',
  'Manual balances rely on posted ledger entries; confirm they match your accounts today.': 'मैनुअल बैलेंस दर्ज और पूरे हो चुके लेनदेन पर आधारित हैं; आज के वास्तविक बैलेंस से उनका मिलान करें।',
  'Loan reserves include every self-reported unpaid installment due through the horizon, including overdue installments. Verify paid counts against lender statements. These estimates exclude fees, floating rates and partial or early principal repayments. Loan dues also entered as recurring or pending expenses are conservatively reserved twice; do not add the same loan again under other obligations.': 'लोन के लिए अलग रखी रकम में इस अवधि तक देय सभी किस्तें शामिल हैं जिन्हें आपने चुकाया हुआ दर्ज नहीं किया है; पुरानी बकाया किस्तें भी शामिल हैं। भुगतान की संख्या ऋणदाता के स्टेटमेंट से जाँचें। शुल्क, बदलती ब्याज दर, आंशिक और समय से पहले मूलधन का भुगतान शामिल नहीं है। वही किस्त आवर्ती या लंबित खर्च में दर्ज होने पर उसकी रकम दो बार अलग रखी जाती है; वही लोन अन्य देनदारियों में फिर से न जोड़ें।',
  'Loan plan changed. Reload before updating.': 'लोन योजना बदल चुकी है। अपडेट करने से पहले रीलोड करें।',
  'Paid installments cannot exceed the loan term': 'चुकाई गई किस्तों की संख्या कुल किस्तों से अधिक नहीं हो सकती।',
  'This workspace has reached its 100 loan-plan limit': 'इस वर्कस्पेस में 100 लोन योजनाओं की सीमा पूरी हो गई है।',
  'Forgot your password?': 'पासवर्ड भूल गए?',
  'Set a new password': 'नया पासवर्ड बनाएँ',
  'Verify your email': 'अपना ईमेल सत्यापित करें',
  'Request verification email': 'सत्यापन ईमेल मँगाएँ',
  'Passwords do not match.': 'दोनों पासवर्ड एक जैसे नहीं हैं।',
  'Password changed. Sign in again on your devices.': 'पासवर्ड बदल गया है। अपने डिवाइस पर फिर से साइन इन करें।',
  'Email verified. You can return to your account.': 'ईमेल सत्यापित हो गया है। अपने अकाउंट पर वापस जाएँ।',
  'If this address is eligible, an email will arrive shortly. Check your spam folder too.': 'यदि यह ईमेल पता योग्य है, तो जल्द ही ईमेल मिलेगा। स्पैम फ़ोल्डर भी देखें।',
  'This link could not be used. It may have expired or already been used. Request a new email.': 'यह लिंक इस्तेमाल नहीं हो सका। इसकी अवधि समाप्त हो सकती है या यह पहले इस्तेमाल हो चुका है। नया ईमेल मँगाएँ।',
  'We could not process your request. Please try again later.': 'आपका अनुरोध पूरा नहीं हो सका। थोड़ी देर बाद फिर कोशिश करें।',
  'Use the email address associated with your FinCo-Pilot account.': 'अपने FinCo-Pilot अकाउंट से जुड़ा ईमेल पता इस्तेमाल करें।',
  'Email': 'ईमेल',
  'New password (8–128 characters)': 'नया पासवर्ड (8–128 अक्षर)',
  'Confirm password': 'पासवर्ड दोबारा लिखें',
  'Open the complete link from your email, or request a new one below.': 'ईमेल में मिला पूरा लिंक खोलें या नीचे नया लिंक मँगाएँ।',
  'Please wait…': 'कृपया प्रतीक्षा करें…',
  'Change password': 'पासवर्ड बदलें',
  'Verify email': 'ईमेल सत्यापित करें',
  'Send email': 'ईमेल भेजें',
  'Back to sign in': 'साइन इन पर वापस जाएँ',
  'Request a new reset link': 'नया पासवर्ड रीसेट लिंक मँगाएँ',
  'Request a new verification link': 'नया सत्यापन लिंक मँगाएँ',
  'The spending plan could not be calculated. Check your connection and try again.': 'खर्च की योजना नहीं बन सकी। इंटरनेट कनेक्शन जाँचकर फिर कोशिश करें।',
  'Safe to spend': 'खर्च करने योग्य रकम',
  'Plan from your current workspace’s cash, debts and upcoming expenses. Review all obligations before relying on an estimate.': 'मौजूदा वर्कस्पेस के पैसे, कर्ज़ और आने वाले खर्चों से योजना बनाएँ। अनुमान पर भरोसा करने से पहले सभी देनदारियाँ जाँचें।',
  'Manage loan and EMI plans': 'लोन और EMI योजनाएँ देखें',
  'Plan for how many days?': 'कितने दिनों की योजना बनाएँ?',
  'Emergency savings to protect': 'आपातकाल के लिए सुरक्षित रखी जाने वाली बचत',
  'Additional goal contributions': 'लक्ष्यों के लिए अतिरिक्त बचत',
  'Other obligations not included in loan plans or scheduled expenses': 'लोन योजनाओं या निर्धारित खर्चों में शामिल न होने वाली अन्य देनदारियाँ',
  'I checked that my balances, upcoming bills and additional obligations are complete and current.': 'मैंने जाँच लिया है कि मेरे बैलेंस, आने वाले बिल और अन्य देनदारियाँ पूरी और अपडेटेड हैं।',
  'Calculating…': 'गणना जारी है…',
  'Calculate spending plan': 'खर्च की योजना बनाएँ',
  'Snapshot:': 'स्थिति की तारीख:',
  '· Through': '· इस तारीख तक',
  'Estimated safe to spend': 'अनुमानित खर्च करने योग्य रकम',
  'per day': 'प्रति दिन',
  'Your plan has a shortfall of': 'आपकी योजना में रकम की कमी है:',
  '. Reduce planned spending or review your obligations.': '। तय खर्च घटाएँ या अपनी देनदारियाँ जाँचें।',
  'Review needed before an amount is available': 'रकम दिखाने से पहले जाँच ज़रूरी है',
  'Cash balance': 'उपलब्ध पैसे',
  'Card debt reserved': 'कार्ड का कर्ज़ चुकाने के लिए रखी रकम',
  'Upcoming outflows reserved': 'आने वाले खर्चों के लिए रखी रकम',
  'Loan installments reserved': 'लोन की किस्तों के लिए रखी रकम',
  'Emergency buffer': 'आपातकालीन बचत',
  'Goal contributions': 'लक्ष्यों के लिए बचत',
  'Other obligations': 'अन्य देनदारियाँ',
  'How this estimate works': 'यह अनुमान कैसे बनता है',
  'Could not save this loan plan. Check your connection, reload the list before retrying, and verify your inputs.': 'लोन योजना सेव नहीं हो सकी। कनेक्शन और दर्ज जानकारी जाँचें। दोबारा कोशिश करने से पहले सूची रीलोड करें।',
  'Loading workspace…': 'वर्कस्पेस लोड हो रहा है…',
  'Loans and EMI plans': 'लोन और EMI योजनाएँ',
  'Monthly fixed-rate, reducing-balance estimates. Payment counts are entered by you, not verified by your bank. Compare the schedule with your lender’s statement.': 'स्थिर ब्याज दर और घटते मूलधन के आधार पर मासिक अनुमान। चुकाई गई किस्तों की संख्या आप दर्ज करते हैं; बैंक ने इसे सत्यापित नहीं किया है। समय-सारणी को अपने ऋणदाता के स्टेटमेंट से मिलाएँ।',
  'Fees, daily interest, floating rates, partial payments and early principal repayments are not modelled. Add those obligations separately. Saving a plan does not create transactions or move money.': 'शुल्क, दैनिक ब्याज, बदलती ब्याज दर, आंशिक भुगतान और समय से पहले मूलधन का भुगतान इस गणना में शामिल नहीं हैं। ये देनदारियाँ अलग से जोड़ें। योजना सेव करने से लेनदेन नहीं बनता और पैसे ट्रांसफ़र नहीं होते।',
  'Open safe-to-spend plan': 'खर्च करने योग्य रकम की योजना खोलें',
  'Add a repayment plan': 'पुनर्भुगतान योजना जोड़ें',
  'Loan name': 'लोन का नाम',
  'Currency': 'मुद्रा',
  'Original principal': 'शुरुआती मूलधन',
  'Annual interest rate (%)': 'वार्षिक ब्याज दर (%)',
  'Total monthly installments': 'कुल मासिक किस्तें',
  'First installment due date': 'पहली किस्त की देय तारीख',
  'Consecutive full installments already paid': 'शुरू से लगातार पूरी चुकाई गई किस्तों की संख्या',
  'The first due date anchors each month. Month-end stays month-end. The final installment adjusts for rounding. Contract inputs stay fixed after saving; archive an incorrect plan before replacing it.': 'पहली देय तारीख से आगे की मासिक तारीखें तय होती हैं। महीने की आख़िरी तारीख आगे भी आख़िरी तारीख रहती है। राउंडिंग का अंतर आख़िरी किस्त में समायोजित होता है। सेव करने के बाद लोन की मूल शर्तें नहीं बदलतीं; गलत योजना को बदलने से पहले आर्काइव करें।',
  'Saving…': 'सेव हो रहा है…',
  'Save loan plan': 'लोन योजना सेव करें',
  'Loading loan plans…': 'लोन योजनाएँ लोड हो रही हैं…',
  'Loan plans could not be loaded.': 'लोन योजनाएँ लोड नहीं हो सकीं।',
  'Retry': 'फिर कोशिश करें',
  'No loan plans in this workspace yet.': 'इस वर्कस्पेस में अभी कोई लोन योजना नहीं है।',
  ' (archived)': ' (आर्काइव किया गया)',
  'Loading repayment schedule…': 'पुनर्भुगतान समय-सारणी लोड हो रही है…',
  'Schedule could not be loaded.': 'समय-सारणी लोड नहीं हो सकी।',
  'Estimated regular installment:': 'अनुमानित नियमित किस्त:',
  '· Total scheduled interest:': '· कुल अनुमानित ब्याज:',
  'Estimated principal remaining after reported payments:': 'दर्ज भुगतानों के बाद अनुमानित बचा मूलधन:',
  'Last manual update:': 'आख़िरी मैनुअल अपडेट:',
  '. Unpaid installments due within your spending horizon, including overdue installments, are reserved in safe-to-spend. An EMI also entered as a recurring or pending expense is conservatively reserved twice. Do not add this plan again under other obligations.': '। योजना की अवधि में देय और पहले से बकाया किस्तों की रकम खर्च करने योग्य रकम से अलग रखी जाती है। वही EMI आवर्ती या लंबित खर्च में भी दर्ज होने पर उसकी रकम सावधानी के लिए दो बार अलग रखी जाती है। इस योजना को अन्य देनदारियों में फिर से न जोड़ें।',
  'Estimated schedule — “reported paid” is your confirmation, not a bank match.': 'अनुमानित समय-सारणी — “भुगतान दर्ज है” आपकी पुष्टि है, बैंक से मिलान नहीं।',
  '#': 'क्रम',
  'Due date': 'देय तारीख',
  'Payment': 'किस्त',
  'Principal': 'मूलधन',
  'Interest': 'ब्याज',
  'Balance': 'बचा मूलधन',
  'Status': 'स्थिति',
  'Reported paid': 'भुगतान दर्ज है',
  'Not reported paid': 'भुगतान दर्ज नहीं है',
  'Consecutive full installments paid (from installment 1)': 'पहली किस्त से लगातार पूरी चुकाई गई किस्तों की संख्या',
  'Archive this plan and remove its reserve from safe-to-spend': 'योजना आर्काइव करें और खर्च की गणना से इसका आरक्षित हिस्सा हटाएँ',
  'I checked my lender’s statement. Any archived loan’s remaining obligations are covered elsewhere in my spending plan.': 'मैंने ऋणदाता का स्टेटमेंट जाँच लिया है। आर्काइव किए गए लोन की बची देनदारियाँ मेरी खर्च योजना में कहीं और शामिल हैं।',
  'Update reported status': 'दर्ज भुगतान की स्थिति अपडेट करें',
}

export function translateLaunch(text: string, language: string): string {
  if (!language.toLowerCase().startsWith('hi')) return text
  if (launchHindi[text]) return launchHindi[text]
  let match = /^A recent exchange rate for (.+) is unavailable\.$/.exec(text)
  if (match) return `${match[1]} के लिए हाल की विनिमय दर उपलब्ध नहीं है।`
  match = /^Reconcile mixed-currency ledger entries in (.+)\.$/.exec(text)
  if (match) return `${match[1]} में अलग-अलग मुद्राओं के लेनदेन का मिलान करें।`
  match = /^Confirm a fresh bank refresh for (.+); a cached ingestion alone is insufficient\.$/.exec(text)
  if (match) return `${match[1]} के लिए बैंक से ताज़ा डेटा आने की पुष्टि करें; केवल पुराना कैश डेटा पर्याप्त नहीं है।`
  match = /^Safe-to-spend is unavailable for (.+): this bank connection does not yet reliably distinguish cash from loan accounts\.$/.exec(text)
  if (match) return `${match[1]} के लिए खर्च करने योग्य रकम उपलब्ध नहीं है: यह बैंक कनेक्शन नकद और लोन खातों में अभी विश्वसनीय अंतर नहीं करता।`
  return text
}

export function useLaunchText() {
  const { i18n } = useTranslation()
  return (text: string) => translateLaunch(text, i18n.language || 'en')
}

export function useLaunchLocale() {
  const { i18n } = useTranslation()
  return resolveSupportedLang(i18n.language)
}
