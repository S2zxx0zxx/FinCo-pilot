"""Reviewed public notice; deployment identity is supplied explicitly, never inferred."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import EmailStr, TypeAdapter

from app.core.retention import BACKUP_MAX_RETENTION_DAYS, SECURITY_LOG_RETENTION_DAYS

if TYPE_CHECKING:
    from app.core.config import Settings

VERSION = "FINCO_PRIVACY_POLICY_V1_2026_10_04"
REVIEWED_ON = "2026-10-04"


def publication_blockers(settings: Settings) -> list[str]:
    missing = []
    for key in (
        "operator_legal_name",
        "privacy_contact_name",
        "privacy_contact_email",
        "privacy_contact_address",
        "privacy_processing_locations",
        "privacy_infrastructure_providers",
    ):
        if not getattr(settings, key).strip():
            missing.append(key)
    if not settings.operator_identity_enabled or settings.operator_country_code.upper() != "IN":
        missing.append("reviewed_operator_identity")
    if settings.privacy_policy_reviewed_version != VERSION:
        missing.append("current_policy_review")
    try:
        effective = date.fromisoformat(settings.privacy_policy_effective_date)
        if effective > date.today():
            missing.append("effective_date_in_future")
    except ValueError:
        missing.append("effective_date")
    return missing


def validate_publication_settings(settings: Settings) -> None:
    public_fields = (
        settings.privacy_contact_name,
        settings.privacy_contact_address,
        settings.privacy_processing_locations,
        settings.privacy_infrastructure_providers,
    )
    if any(
        len(value) > 500 or any(ord(c) < 32 for c in value) or "://" in value
        for value in public_fields
    ):
        raise ValueError(
            "Privacy public fields require bounded plain text, not URLs or control characters"
        )
    if settings.privacy_contact_email:
        settings.privacy_contact_email = str(
            TypeAdapter(EmailStr).validate_python(settings.privacy_contact_email)
        )
    if settings.privacy_policy_published and publication_blockers(settings):
        raise ValueError(
            "Privacy publication requires verified public identity, contact, deployment facts, date and current review"
        )


def section(key, en_title, hi_title, en, hi):
    return {"id": key, "title": {"en": en_title, "hi": hi_title}, "body": {"en": en, "hi": hi}}


SECTIONS = [
    section(
        "scope",
        "Who this notice covers",
        "यह नोटिस किसके लिए है",
        "This notice describes FinCo-Pilot accounts, financial workspaces, support and optional integrations. Your workspace issuer is separate from the service operator named above. A self-hosted installation is operated by its own administrator, whose identity, recipients and locations must be disclosed here. Reading this notice is not consent to every optional use or a waiver of your rights.",
        "यह नोटिस FinCo-Pilot अकाउंट, वित्तीय वर्कस्पेस, सहायता और वैकल्पिक इंटीग्रेशन के बारे में है। आपके वर्कस्पेस का इनवॉइस जारीकर्ता ऊपर बताए सेवा संचालक से अलग है। खुद होस्ट किए गए इंस्टॉलेशन का संचालक उसका अपना एडमिन होता है; उसकी पहचान, डेटा प्राप्तकर्ता और स्थान यहाँ बताए जाने चाहिए। यह नोटिस पढ़ना हर वैकल्पिक उपयोग की सहमति या अधिकार छोड़ना नहीं है।",
    ),
    section(
        "account",
        "Account and security information",
        "अकाउंट और सुरक्षा की जानकारी",
        "We process your email, profile/preferences, password hash and account/workspace identifiers to create and secure your account. If enabled, we store encrypted authenticator secrets, hashed recovery codes and passkey public credentials; your device's fingerprint or face template is not sent to this app by passkey authentication. Optional identity-provider login supplies identity/email claims. Verification/reset emails contain short-lived links; the email provider processes the address, message and delivery metadata. Security controls use temporary challenges, rate limits, IP/request metadata and audit records.",
        "अकाउंट बनाने और सुरक्षित रखने के लिए ईमेल, प्रोफ़ाइल/पसंद, पासवर्ड का हैश और अकाउंट/वर्कस्पेस पहचान का उपयोग होता है। चालू होने पर एन्क्रिप्ट किए गए authenticator secrets, recovery codes के हैश और passkey के सार्वजनिक credentials रखे जाते हैं; passkey लॉगिन में डिवाइस का फिंगरप्रिंट या चेहरे का टेम्पलेट इस ऐप को नहीं भेजा जाता। वैकल्पिक identity-provider लॉगिन से पहचान/ईमेल claims मिलते हैं। सत्यापन और reset ईमेल में सीमित समय वाले लिंक होते हैं; ईमेल प्रदाता पता, संदेश और delivery metadata प्रोसेस करता है। सुरक्षा में अस्थायी challenges, rate limits, IP/request metadata और audit records उपयोग होते हैं।",
    ),
    section(
        "finance",
        "Financial records and sharing",
        "वित्तीय रिकॉर्ड और शेयरिंग",
        "Records you enter/import may include account names, balances, transactions, payees, categories, budgets, goals, debts, investments and uploaded documents. Invoice records can include issuer/customer names, contact/address/tax details and payment instructions. We use these to organize your money, reconcile records, calculate estimates, generate reports/invoices and provide the features you request. Workspace members see data according to their roles. Shared invoice links allow recipients holding the link to view its invoice; treat the link as a credential and revoke sharing when needed. Avoid uploading unrelated sensitive information or another person's records without authority.",
        "आपके दर्ज/इम्पोर्ट किए रिकॉर्ड में अकाउंट नाम, बैलेंस, लेनदेन, payees, categories, बजट, लक्ष्य, कर्ज़, निवेश और अपलोड दस्तावेज़ हो सकते हैं। इनवॉइस में जारीकर्ता/ग्राहक के नाम, संपर्क/पता/टैक्स जानकारी और भुगतान निर्देश हो सकते हैं। इनसे पैसे व्यवस्थित करना, रिकॉर्ड मिलाना, अनुमान, रिपोर्ट/इनवॉइस और माँगी गई सुविधाएँ देना संभव होता है। वर्कस्पेस सदस्य अपनी भूमिका के अनुसार डेटा देखते हैं। शेयर किए इनवॉइस का लिंक रखने वाला व्यक्ति उसे देख सकता है; लिंक को credential की तरह संभालें और आवश्यकता पर sharing बंद करें। अनावश्यक संवेदनशील जानकारी या बिना अधिकार किसी दूसरे के रिकॉर्ड अपलोड न करें।",
    ),
    section(
        "integrations",
        "Optional banks, payments and support",
        "वैकल्पिक बैंक, भुगतान और सहायता",
        "Bank connectors such as Pluggy, Enable Banking or a chosen SimpleFIN server may exchange consent/session tokens, account identity, balances and transactions when you connect them. Their availability and terms depend on the deployment; this is not a claim that FinCo-Pilot is an Indian Account Aggregator or FIU. When checkout is enabled, Razorpay processes payment details; this app retains order/payment/subscription references, amounts and verification state, not full card PAN or CVV. Support receives the contact and message you submit, category and limited diagnostics; Zoho Desk may receive tickets when configured. Do not send passwords, OTPs or raw financial dumps in support. Separate security reports may go to GitHub when you choose its reporting link.",
        "Pluggy, Enable Banking या चुने गए SimpleFIN server से कनेक्ट करने पर consent/session tokens, अकाउंट पहचान, बैलेंस और लेनदेन का आदान-प्रदान हो सकता है। उपलब्धता और शर्तें इंस्टॉलेशन पर निर्भर हैं; इससे FinCo-Pilot के Indian Account Aggregator या FIU होने का दावा नहीं होता। Checkout चालू होने पर Razorpay भुगतान विवरण प्रोसेस करता है; ऐप order/payment/subscription references, रकम और verification state रखता है, पूरा card PAN या CVV नहीं। सहायता में आपके भेजे संपर्क/संदेश, category और सीमित diagnostics जाते हैं; configure होने पर Zoho Desk को tickets मिल सकते हैं। सहायता में passwords, OTPs या पूरे वित्तीय dumps न भेजें। अलग security report का लिंक चुनने पर report GitHub को जा सकती है।",
    ),
    section(
        "ai",
        "AI prompts, documents and tools",
        "AI prompts, दस्तावेज़ और tools",
        "If you use Copilot/Agents, prompts, conversation history, selected page/financial context, knowledge-document text/embeddings and tool results may be processed to answer or perform an authorized task. Uploaded knowledge files and conversations can remain stored. A self-hosted router does not make an external model/search provider private: the selected upstream can receive the request context. User-configured model endpoints and external MCP servers are additional recipients under their own terms. Their retention, training and location policies must be checked before sharing. We do not promise that all AI stays on your device or that every provider has zero retention. Do not put passwords/API keys into prompts.",
        "Copilot/Agents उपयोग करने पर prompts, बातचीत का इतिहास, चुना गया page/वित्तीय context, knowledge document का text/embeddings और tool results जवाब देने या अधिकृत काम के लिए प्रोसेस हो सकते हैं। Knowledge files और बातचीत संग्रहित रह सकते हैं। Router खुद होस्ट होने से बाहरी model/search provider निजी नहीं हो जाता; चुने upstream को request context मिल सकता है। आपके configure किए model endpoints और बाहरी MCP servers अपनी शर्तों के तहत अतिरिक्त डेटा प्राप्तकर्ता हैं। साझा करने से पहले उनकी retention, training और location policies जाँचें। हम यह वादा नहीं करते कि सभी AI डिवाइस पर रहती है या हर प्रदाता zero retention रखता है। Prompts में passwords/API keys न डालें।",
    ),
    section(
        "recipients",
        "Recipients, locations and disclosures",
        "डेटा प्राप्तकर्ता, स्थान और खुलासे",
        "Hosting/database, object storage, backup, email, security edge, optional identity, payment, support and AI providers may process relevant data to deliver the service. The deployment-specific infrastructure and locations are shown above; configuration is a disclosure, not independent proof of provider compliance. Neon, Cloudflare R2/edge and Zoho Desk are launch selections in the project, not evidence that each is active here. Market-rate/symbol lookups use public queries and network metadata rather than your transaction history. Providers or their subproviders may operate outside India; no all-data-in-India guarantee is made. Disclosures required by applicable law, lawful authority or protection against fraud/security incidents are limited to the relevant purpose. This app has no advertising-data-sale feature; external providers' own practices require separate review.",
        "सेवा देने के लिए hosting/database, object storage, backup, email, security edge और वैकल्पिक identity, payment, support तथा AI providers संबंधित डेटा प्रोसेस कर सकते हैं। इस इंस्टॉलेशन के infrastructure और स्थान ऊपर दिए हैं; configuration एक खुलासा है, प्रदाता के compliance का स्वतंत्र प्रमाण नहीं। Neon, Cloudflare R2/edge और Zoho Desk परियोजना के launch selections हैं, इससे यहाँ सबके चालू होने का प्रमाण नहीं मिलता। Market-rate/symbol lookup में सार्वजनिक queries और network metadata जाते हैं, आपका transaction history नहीं। Providers या उनके subproviders भारत के बाहर काम कर सकते हैं; सभी डेटा भारत में रखने की गारंटी नहीं है। लागू कानून, वैध प्राधिकरण या fraud/security incident के लिए खुलासा संबंधित उद्देश्य तक सीमित रहता है। ऐप में advertising-data-sale की सुविधा नहीं है; बाहरी प्रदाताओं की प्रक्रियाएँ अलग जाँचनी होंगी।",
    ),
    section(
        "storage",
        "Browser storage and cookies",
        "ब्राउज़र storage और cookies",
        "The browser keeps a sign-in token, workspace selection, language/theme/UI preferences and some navigation/install state in local/session storage. Language detection may read a language cookie. Clearing site data removes local settings and signs you out but does not delete server records. The app may cache its public shell/assets for installation; sensitive API responses are not intended for offline caching. It does not bundle advertising analytics/tracking pixels. Edge/payment/identity/support sites may use their own cookies/storage when you interact with them; their notices apply. Browser privacy mode only masks displayed amounts, not stored data or member access.",
        "ब्राउज़र local/session storage में sign-in token, workspace selection, भाषा/theme/UI पसंद और कुछ navigation/install state रखता है। भाषा पहचानने के लिए language cookie पढ़ी जा सकती है। Site data साफ़ करने से स्थानीय सेटिंग्स हटती हैं और sign out होता है, server records delete नहीं होते। Installation के लिए सार्वजनिक app shell/assets cache हो सकते हैं; संवेदनशील API responses offline caching के लिए नहीं हैं। ऐप में advertising analytics/tracking pixels bundle नहीं हैं। Edge/payment/identity/support sites से संपर्क पर उनकी cookies/storage और notices लागू हो सकते हैं। Privacy mode केवल स्क्रीन पर रकम छिपाता है, stored data या सदस्यों की पहुँच नहीं।",
    ),
    section(
        "retention",
        "Retention and deletion limits",
        "डेटा रखने और हटाने की सीमाएँ",
        f"Financial/account/workspace and AI history records follow their active purpose. The engineering policy targets {SECURITY_LOG_RETENTION_DAYS} days for minimized security/audit/AI-usage evidence and closed support tickets, 30 days for abandoned checkout and sensitive MCP argument payloads, and at most {BACKUP_MAX_RETENTION_DAYS} days for ordinary encrypted backups. These are policy targets: several expiry jobs and live provider deletion remain pending, so elapsed time alone does not prove erasure. Redis challenges expire by TTL and are excluded from backups. Payment/tax/dispute records may need longer justified retention; provider contractual obligations can differ. Shared-workspace data is not automatically destroyed when a member leaves, and archive is not hard deletion. Personal account deletion uses an operator-reviewed workflow that preserves shared records and requires actual provider/hold evidence and verified backup expiry. It is not unattended provider erasure. Shared-workspace hard deletion and several expiry jobs remain pending. Backup restore stays quarantined until current deletion/hold/payment facts are reconciled.",
        f"वित्तीय/account/workspace और AI history records अपने सक्रिय उद्देश्य के अनुसार रखे जाते हैं। Engineering policy में सीमित security/audit/AI-usage evidence और बंद support tickets के लिए {SECURITY_LOG_RETENTION_DAYS} दिन, abandoned checkout और संवेदनशील MCP arguments के लिए 30 दिन तथा सामान्य encrypted backups के लिए अधिकतम {BACKUP_MAX_RETENTION_DAYS} दिन का लक्ष्य है। ये policy targets हैं: कई expiry jobs और live provider deletion अभी pending हैं; समय बीतना डेटा मिटने का प्रमाण नहीं। Redis challenges TTL से समाप्त होते हैं और backup में नहीं जाते। Payment/tax/dispute records का उचित कारण से लंबा retention हो सकता है; provider contracts अलग हो सकते हैं। सदस्य के जाने से shared-workspace data अपने आप नष्ट नहीं होता और archive hard deletion नहीं है। व्यक्तिगत खाता हटाने की संचालक-समीक्षित प्रक्रिया साझा रिकॉर्ड सुरक्षित रखती है और वास्तविक प्रदाता/डेटा रोक के प्रमाण तथा सत्यापित बैकअप समाप्ति माँगती है। यह बिना समीक्षा के प्रदाता से डेटा मिटाने की प्रक्रिया नहीं है। साझा कार्यक्षेत्र पूरी तरह हटाने और कई expiry jobs का काम लंबित है। Restore के बाद वर्तमान deletion/hold/payment तथ्य मिलाने तक backup data quarantine में रहता है।",
    ),
    section(
        "choices",
        "Your choices, requests and grievances",
        "आपके विकल्प, अनुरोध और शिकायतें",
        "You can review/edit available records, use supported exports, manage authorized sharing/connections and avoid optional integrations. The workspace export contains selected records, not every attached file or authentication setting. Ask the privacy/grievance contact above for access/correction, consent withdrawal, deletion or concerns about processing; necessary identity checks protect your data without asking for passwords/OTPs. Withdrawing a necessary permission may prevent the affected service, not unrelated features. A request is not a guarantee that all copies have already been deleted; shared records, legal holds and provider retention must be addressed. Where the SPDI grievance rule applies, grievances must be redressed expeditiously and within one month. Other rights and escalation routes depend on the law then in force. This notice does not certify legal compliance or claim every future DPDP right is already operational.",
        "उपलब्ध रिकॉर्ड देख/सुधार सकते हैं, supported exports उपयोग कर सकते हैं, अधिकृत sharing/connections सँभाल सकते हैं और वैकल्पिक integrations से बच सकते हैं। Workspace export में चुनिंदा रिकॉर्ड होते हैं, हर attached file या authentication setting नहीं। Access/correction, consent withdrawal, deletion या processing की शिकायत के लिए ऊपर दिए privacy/grievance contact को लिखें; आवश्यक पहचान जाँच passwords/OTPs माँगे बिना डेटा की रक्षा करती है। ज़रूरी permission वापस लेने से संबंधित सेवा रुक सकती है, असंबंधित सुविधाएँ नहीं। अनुरोध भेजने से सभी copies पहले ही delete हो जाने की गारंटी नहीं; shared records, legal holds और provider retention देखना पड़ता है। जहाँ SPDI grievance rule लागू है, शिकायतों का निवारण जल्दी और एक महीने के भीतर होना चाहिए। अन्य अधिकार/शिकायत के रास्ते उस समय लागू कानून पर निर्भर हैं। यह नोटिस legal compliance प्रमाणपत्र या भविष्य के हर DPDP अधिकार के अभी चालू होने का दावा नहीं है।",
    ),
    section(
        "security",
        "Security and incidents",
        "सुरक्षा और incidents",
        "Controls include role/workspace access checks, password hashing, encrypted recoverable credentials, private object access, bounded auth links/quotas, secret separation and isolated encrypted restore checks. Production TLS, providers, logs and expiry must be verified in the actual deployment. No system is risk-free and this is not end-to-end encryption against the operator. Suspected exposure is reviewed, contained and handled with notifications required by the applicable law; this notice does not assert a blanket incident deadline. Use the privacy contact for concerns and private security reporting for vulnerabilities. Do not post user data or credentials in public reports.",
        "सुरक्षा में role/workspace access checks, password hashing, recoverable credentials का encryption, निजी object access, सीमित auth links/quotas, अलग secrets और isolated encrypted restore checks शामिल हैं। वास्तविक deployment में production TLS, providers, logs और expiry verify होने चाहिए। कोई system जोखिम-रहित नहीं; यह operator से सुरक्षित end-to-end encryption नहीं है। संदिग्ध exposure की जाँच, containment और लागू कानून के अनुसार notification की जाती है; यह नोटिस हर incident के लिए एक जैसा deadline नहीं बताता। चिंताओं के लिए privacy contact और vulnerabilities के लिए private security reporting उपयोग करें। सार्वजनिक reports में user data या credentials न डालें।",
    ),
    section(
        "children",
        "Adults and information about others",
        "वयस्क और दूसरों की जानकारी",
        "FinCo-Pilot is intended for adults aged 18 or over. It currently provides no verified parental-consent workflow. Do not create a child's account or upload children's information for processing here. If such information is discovered, contact the operator for restriction and an appropriate deletion/legal review. Only submit other people's information where you have authority and the relevant notice/permission.",
        "FinCo-Pilot 18 वर्ष या अधिक उम्र के वयस्कों के लिए है। अभी verified parental-consent workflow उपलब्ध नहीं है। यहाँ बच्चे का अकाउंट न बनाएँ या processing के लिए बच्चों की जानकारी अपलोड न करें। ऐसी जानकारी मिलने पर restriction और उचित deletion/legal review के लिए operator से संपर्क करें। दूसरों की जानकारी तभी भेजें जब आपके पास अधिकार और संबंधित notice/permission हो।",
    ),
    section(
        "changes",
        "Changes and legal timing",
        "बदलाव और कानूनी समय-सीमा",
        "The version and effective date are displayed above. Material changes to purposes, recipients or processing require review and any notice/permission required by applicable law; a new policy does not retrospectively authorize unrelated use. India's DPDP Act/Rules have phased commencement: as reviewed on 4 October 2026, core notice/processing/rights rules are scheduled for the eighteen-month phase, rather than all being in force today. Existing applicable SPDI/security obligations still need review. Recheck official law, operator facts and live deployment before publication and when they change.",
        "Version और प्रभावी तारीख ऊपर दी गई हैं। उद्देश्य, डेटा प्राप्तकर्ता या processing के महत्वपूर्ण बदलाव की समीक्षा तथा लागू कानून के अनुसार notice/permission ज़रूरी है; नई policy पुराने असंबंधित उपयोग को बाद में अनुमति नहीं देती। भारत के DPDP Act/Rules चरणों में लागू होते हैं: 4 अक्टूबर 2026 की समीक्षा के अनुसार मुख्य notice/processing/rights rules अठारह-महीने वाले चरण के लिए निर्धारित हैं, सभी आज लागू नहीं हैं। वर्तमान लागू SPDI/security दायित्वों की समीक्षा फिर भी आवश्यक है। Publication से पहले और बदलाव पर official law, operator facts तथा live deployment दोबारा जाँचें।",
    ),
]


def public_policy(settings: Settings) -> dict:
    blockers = publication_blockers(settings)
    published = settings.privacy_policy_published and not blockers
    return {
        "version": VERSION,
        "reviewed_on": REVIEWED_ON,
        "status": "published" if published else "draft",
        "effective_date": settings.privacy_policy_effective_date if published else None,
        "operator": {
            "brand_name": settings.operator_brand_name,
            "legal_name": (settings.operator_legal_name or None)
            if settings.operator_identity_enabled
            else None,
            "entity_type": settings.operator_entity_type,
            "country_code": settings.operator_country_code,
        },
        "contact": {
            "name": settings.privacy_contact_name or None,
            "email": settings.privacy_contact_email or None,
            "address": settings.privacy_contact_address or None,
        },
        "deployment": {
            "providers": settings.privacy_infrastructure_providers or None,
            "locations": settings.privacy_processing_locations or None,
        },
        "sections": SECTIONS,
    }
