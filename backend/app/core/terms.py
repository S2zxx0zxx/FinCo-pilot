"""Public terms grounded in the current build, not a fictitious paid lifecycle."""

from __future__ import annotations

from datetime import date
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import EmailStr, TypeAdapter

from app.core.privacy_policy import publication_blockers as privacy_blockers, section

if TYPE_CHECKING:
    from app.core.config import Settings

VERSION = "FINCO_TERMS_V1_2026_10_04"
REVIEWED_ON = "2026-10-04"
CONTACT_FIELDS = (
    "terms_contact_name",
    "terms_contact_email",
    "terms_contact_address",
    "terms_contact_phone",
    "terms_contact_designation",
    "terms_public_website",
)
COMMERCIAL_FIELDS = (
    "terms_refund_policy_en",
    "terms_refund_policy_hi",
    "terms_cancellation_policy_en",
    "terms_cancellation_policy_hi",
)


def publication_blockers(settings: Settings) -> list[str]:
    blockers = [
        key
        for key in ("operator_legal_name", *CONTACT_FIELDS, *COMMERCIAL_FIELDS)
        if not getattr(settings, key).strip()
    ]
    if (
        not settings.operator_identity_enabled
        or settings.operator_country_code.strip().upper() != "IN"
    ):
        blockers.append("reviewed_operator_identity")
    if settings.terms_reviewed_version != VERSION:
        blockers.append("current_terms_review")
    try:
        if date.fromisoformat(settings.terms_effective_date) > date.today():
            blockers.append("effective_date_in_future")
    except ValueError:
        blockers.append("effective_date")
    if not settings.privacy_policy_published or privacy_blockers(settings):
        blockers.append("published_privacy_notice")
    # There is no signed recurring/refund/fulfilment lifecycle in this build.
    if settings.billing_checkout_enabled:
        blockers.append("paid_lifecycle_not_ready")
    return blockers


def validate_publication_settings(settings: Settings) -> None:
    for key in (*CONTACT_FIELDS, *COMMERCIAL_FIELDS):
        value = getattr(settings, key)
        limit = 2000 if key in COMMERCIAL_FIELDS else 500
        if len(value) > limit or any(ord(c) < 32 for c in value):
            raise ValueError("Terms public fields require bounded text without control characters")
        if key != "terms_public_website" and "://" in value:
            raise ValueError("Terms public text must not contain URLs or connection strings")
    if settings.terms_contact_email:
        settings.terms_contact_email = str(
            TypeAdapter(EmailStr).validate_python(settings.terms_contact_email)
        )
    if settings.terms_contact_phone and (
        not re.fullmatch(r"\+?[0-9 ().-]{6,40}", settings.terms_contact_phone)
        or len(re.sub(r"\D", "", settings.terms_contact_phone)) < 6
    ):
        raise ValueError("Terms contact phone requires a bounded public phone number")
    if settings.terms_public_website:
        url = urlsplit(settings.terms_public_website)
        _ = url.port  # Reject invalid port declarations without making network requests.
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or "\\" in settings.terms_public_website
        ):
            raise ValueError(
                "Terms website requires a public HTTPS URL without credentials, query or fragment"
            )
    if settings.terms_published and publication_blockers(settings):
        raise ValueError(
            "Terms publication requires current review, public contact, commercial decisions, privacy publication and disabled unfinished checkout"
        )


SECTIONS = [
    section(
        "scope",
        "Service and operator",
        "सेवा और संचालक",
        "These terms describe the FinCo-Pilot installation operated by the legal person identified above. A workspace's invoice issuer is not automatically the platform operator. Self-hosted administrators are responsible for their own deployment and disclosures. Draft terms are not an effective published contract. Displaying, reading or registering does not prove recorded acceptance of a particular version; this build has no durable terms-acceptance ledger. Binding acceptance and material-change notices must be implemented and reviewed before a paid launch.",
        "ये शर्तें ऊपर पहचाने गए कानूनी व्यक्ति द्वारा संचालित FinCo-Pilot सेवा के बारे में हैं। कार्यक्षेत्र का चालान जारीकर्ता अपने आप मंच का संचालक नहीं होता। स्वयं सेवा चलाने वाला प्रशासक अपने संचालन और खुलासों के लिए जिम्मेदार है। मसौदा प्रभावी प्रकाशित अनुबंध नहीं है। शर्तें दिखाना, पढ़ना या पंजीकरण करना किसी खास संस्करण की दर्ज स्वीकृति का प्रमाण नहीं है; इस संस्करण में स्वीकृति का स्थायी अभिलेख नहीं है। सशुल्क शुरुआत से पहले बाध्यकारी स्वीकृति और महत्वपूर्ण बदलाव की सूचना व्यवस्था बनाकर समीक्षा करनी होगी।",
    ),
    section(
        "eligibility",
        "Eligibility and account security",
        "पात्रता और खाते की सुरक्षा",
        "The service is intended for adults aged 18 or over who are legally competent to contract, or authorized representatives of a workspace. No verified age/parental-consent workflow is provided. Supply accurate account information, protect your sign-in credentials and recovery methods, and report suspected unauthorized access. Do not share passwords, OTPs or recovery codes with support. Your responsibilities do not remove the operator's own security or legal duties.",
        "सेवा 18 वर्ष या अधिक उम्र के अनुबंध करने के कानूनी रूप से सक्षम वयस्कों और कार्यक्षेत्र के अधिकृत प्रतिनिधियों के लिए है। उम्र या अभिभावक की सहमति सत्यापित करने की व्यवस्था उपलब्ध नहीं है। खाते की सही जानकारी दें, प्रवेश और पुनर्प्राप्ति साधनों की रक्षा करें और अनधिकृत पहुँच के संदेह की सूचना दें। सहायता में पासवर्ड, एकबारगी कूट या पुनर्प्राप्ति कूट साझा न करें। आपकी जिम्मेदारियों से संचालक के सुरक्षा या कानूनी दायित्व समाप्त नहीं होते।",
    ),
    section(
        "finance",
        "Financial tools and estimates",
        "वित्तीय साधन और अनुमान",
        "FinCo-Pilot organizes records, budgets, goals, reports and invoices. Safe-to-spend amounts, forecasts, tax/debt calculations, market prices and AI outputs are estimates dependent on inputs, timing and assumptions. Verify important decisions against original bank/provider records and qualified advice. The app is not a bank, deposit taker, Indian Account Aggregator/FIU, or a claim of licensed investment/tax advice. It does not guarantee returns, debt outcomes or statutory filing accuracy.",
        "FinCo-Pilot रिकॉर्ड, बजट, लक्ष्य, रिपोर्ट और चालान व्यवस्थित करता है। सुरक्षित खर्च की रकम, भविष्य के अनुमान, कर और कर्ज़ की गणना, बाजार भाव तथा कृत्रिम बुद्धिमत्ता के उत्तर दी गई जानकारी, समय और मान्यताओं पर निर्भर अनुमान हैं। महत्वपूर्ण निर्णय मूल बैंक या प्रदाता के रिकॉर्ड और योग्य सलाह से जाँचें। यह बैंक, जमा स्वीकार करने वाली संस्था, भारतीय खाता समेकक या वित्तीय सूचना उपयोगकर्ता होने अथवा अधिकृत निवेश या कर सलाह देने का दावा नहीं है। लाभ, कर्ज़ के परिणाम या वैधानिक विवरण की शुद्धता की गारंटी नहीं है।",
    ),
    section(
        "sharing",
        "Your content and shared workspaces",
        "आपकी सामग्री और साझा कार्यक्षेत्र",
        "You retain rights in the records/documents you submit and must have authority to submit or share other people's data. Give the operator only the permission needed to host, process and display content for requested features and lawful service/security obligations, not a blanket right to sell it or train unrelated models. Workspace roles control access; invoice bearer links can expose their invoice to anyone holding the link. Review membership and revoke links when appropriate. Leaving a shared workspace or archiving it is not erasure of its records.",
        "आपके भेजे रिकॉर्ड और दस्तावेज़ों पर आपके अधिकार रहते हैं; दूसरे लोगों की जानकारी भेजने या साझा करने का अधिकार आपके पास होना चाहिए। माँगी गई सुविधाओं और वैध सेवा या सुरक्षा दायित्वों के लिए आवश्यक संग्रहण, संसाधन और प्रदर्शन की अनुमति दें; सामग्री बेचने या असंबंधित मॉडल सिखाने का असीमित अधिकार नहीं। कार्यक्षेत्र की भूमिकाएँ पहुँच तय करती हैं; चालान का लिंक रखने वाला व्यक्ति उसका चालान देख सकता है। सदस्यता जाँचें और उचित समय पर लिंक बंद करें। साझा कार्यक्षेत्र छोड़ना या संग्रहित करना उसके रिकॉर्ड मिटाना नहीं है।",
    ),
    section(
        "ai",
        "AI and external tools",
        "कृत्रिम बुद्धिमत्ता और बाहरी साधन",
        "Optional AI can make mistakes, omit context and receive sensitive prompts/documents through selected providers or external MCP tools. Check results and review the recipient before sharing. Tool permissions and approval rules apply to supported actions, but do not guarantee every external server's safety. Do not put credentials in prompts or authorize actions you do not understand. Provider availability, retention and terms differ; a local router does not make external AI private. No autonomous bank-money movement, guaranteed financial advice or unlimited provider capacity is promised.",
        "वैकल्पिक कृत्रिम बुद्धिमत्ता गलती कर सकती है, संदर्भ छोड़ सकती है और चुने प्रदाताओं या बाहरी साधनों के माध्यम से संवेदनशील प्रश्न और दस्तावेज़ प्राप्त कर सकती है। परिणाम जाँचें और साझा करने से पहले प्राप्तकर्ता की समीक्षा करें। समर्थित कामों पर अनुमति और स्वीकृति नियम लागू हैं, पर हर बाहरी सर्वर की सुरक्षा की गारंटी नहीं है। प्रश्नों में प्रवेश कूट न डालें और बिना समझे काम की अनुमति न दें। प्रदाताओं की उपलब्धता, संग्रहण अवधि और शर्तें अलग होती हैं; स्थानीय मार्गनिर्देशक से बाहरी सेवा निजी नहीं हो जाती। अपने आप बैंक का पैसा भेजना, सुनिश्चित वित्तीय सलाह या असीमित क्षमता का वादा नहीं है।",
    ),
    section(
        "pricing",
        "Plans, offers and fulfilment",
        "योजनाएँ, प्रस्ताव और सेवा देना",
        "The displayed server catalog and checkout reservation determine the quoted plan, interval, currency, tax display, service start and amount. Founder offers are introductory acquisition prices, not lifetime or permanent discounted subscriptions; eligibility and capacity are server-owned. The pre-release founder contract provides 60 days from the configured public launch, not an invented launch date. Verification of a captured test payment records purchase evidence but does not activate Pro/Max. This build refuses live Razorpay order collection; signed paid activation and recurring fulfilment remain pending. Catalog prices and renewal descriptions are not proof of an active billing mandate.",
        "सर्वर की प्रदर्शित सूची और भुगतान आरक्षण से योजना, अवधि, मुद्रा, कर का प्रदर्शन, सेवा की शुरुआत और रकम तय होते हैं। शुरुआती सदस्य प्रस्ताव प्रथम खरीद के लिए हैं; आजीवन या स्थायी रियायती सदस्यता नहीं। पात्रता और क्षमता सर्वर तय करता है। विमोचन से पहले के प्रस्ताव में तय सार्वजनिक शुरुआत से 60 दिन मिलते हैं; कोई काल्पनिक शुरुआत की तारीख नहीं है। परीक्षण में प्राप्त भुगतान का सत्यापन खरीद का प्रमाण दर्ज करता है, लेकिन Pro या Max सक्रिय नहीं करता। इस संस्करण में Razorpay से वास्तविक पैसे लेना रोका गया है; सुरक्षित सशुल्क सक्रियकरण और नियमित सेवा व्यवस्था अभी बाकी है। सूची के मूल्य या आगामी शुल्क का उल्लेख सक्रिय भुगतान आदेश का प्रमाण नहीं है।",
    ),
    section(
        "cancellation",
        "Renewals, cancellation and refunds",
        "नवीनीकरण, रद्द करना और धनवापसी",
        "There is no operational automated recurring-charge, subscription-cancellation or refund executor in this build. Closing checkout releases an unverified price reservation, not a verified payment refund or bank mandate. Do not assume deleting an account stops a provider charge. Operator-specific reviewed refund and cancellation decisions appear above when supplied; before paid launch disclose eligibility, request method/window, service period, taxes and actual refund timing. Request review of duplicate/failed/misdescribed charges through the contact above without sending card secrets. No blanket no-refund rule, automatic instant refund or mandatory-rights waiver is imposed. Provider processing time is separate from merchant eligibility and cannot be guaranteed here.",
        "इस संस्करण में अपने आप नियमित शुल्क लेना, सदस्यता रद्द करना या धनवापसी करना चालू नहीं है। भुगतान खिड़की बंद करने से असत्यापित मूल्य आरक्षण छूटता है; सत्यापित भुगतान वापस नहीं होता और बैंक का आदेश बंद नहीं होता। खाता मिटाने से प्रदाता का शुल्क रुक जाने की धारणा न बनाएँ। संचालक की समीक्षा की हुई धनवापसी और रद्द करने की शर्तें मिलने पर ऊपर दिखती हैं। सशुल्क शुरुआत से पहले पात्रता, अनुरोध का तरीका और अवधि, सेवा अवधि, कर तथा वास्तविक धनवापसी समय स्पष्ट करें। दोहरे, विफल या गलत विवरण वाले शुल्क की समीक्षा ऊपर के संपर्क से माँगें; कार्ड के गुप्त कूट न भेजें। हर स्थिति में धनवापसी रोकने, तुरंत धनवापसी या अनिवार्य अधिकार छोड़ने की शर्त नहीं लगाई गई है। प्रदाता का समय व्यापारी की पात्रता से अलग है और यहाँ उसकी गारंटी नहीं है।",
    ),
    section(
        "acceptable-use",
        "Acceptable use",
        "उचित उपयोग",
        "Do not use the service for fraud, unlawful access, credential theft, malware, harassment, unauthorized data disclosure, quota/rate-limit evasion or impersonation. Do not misrepresent generated invoices or reports as bank statements or official filings. Authorized good-faith security research should follow the private reporting route without exposing user records. Applicable third-party licenses and terms still apply; this notice does not grant rights to their content or services.",
        "सेवा का उपयोग धोखाधड़ी, अवैध प्रवेश, कूट चोरी, हानिकारक सॉफ्टवेयर, उत्पीड़न, अनधिकृत खुलासे, सीमा से बचने या किसी और की पहचान लेने के लिए न करें। बने चालान और रिपोर्ट को बैंक विवरण या आधिकारिक दाखिला बताकर प्रस्तुत न करें। अधिकृत सद्भावपूर्ण सुरक्षा जाँच निजी सूचना मार्ग से करें और उपयोगकर्ताओं के रिकॉर्ड उजागर न करें। तीसरे पक्ष की अनुमति और शर्तें लागू रहती हैं; यह सूचना उनकी सामग्री या सेवा के अधिकार नहीं देती।",
    ),
    section(
        "availability",
        "Availability and changes",
        "उपलब्धता और बदलाव",
        "Features depend on deployment, plan limits and external providers. Maintenance, outages or security containment can interrupt access; no live uptime/RPO/RTO SLA is established by this notice. Material price or purpose changes require clear prospective notice and any legally required agreement. New terms do not retrospectively authorize unrelated processing or remove accrued rights. Review a new version before relying on it; merely changing this page is not proof that users accepted it.",
        "सुविधाएँ संचालन, योजना की सीमाओं और बाहरी प्रदाताओं पर निर्भर हैं। रखरखाव, खराबी या सुरक्षा कार्रवाई से पहुँच रुक सकती है; यह सूचना उपलब्धता या पुनर्प्राप्ति समय की वास्तविक सेवा गारंटी नहीं बनाती। मूल्य या उद्देश्य के महत्वपूर्ण बदलाव पर पहले स्पष्ट सूचना और कानून के अनुसार आवश्यक सहमति चाहिए। नई शर्तें पुराने असंबंधित उपयोग को अनुमति नहीं देतीं और अर्जित अधिकार नहीं हटातीं। नए संस्करण पर निर्भर होने से पहले समीक्षा करें; पृष्ठ बदल देना उपयोगकर्ताओं की स्वीकृति का प्रमाण नहीं है।",
    ),
    section(
        "exit",
        "Restrictions, exit and your records",
        "प्रतिबंध, सेवा छोड़ना और आपके रिकॉर्ड",
        "Access may be restricted where necessary for verified security, abuse or lawful obligations; contact the operator for review. Provide reasons and a reasonable remedy/export opportunity where lawful and practicable, without delaying urgent containment. Export currently covers supported records and is not guaranteed to include every file/auth setting. Lower-plan overages restrict creation rather than proving records were deleted. Personal account deletion uses a separate operator-reviewed workflow with fresh authentication, shared-data preservation, provider evidence and backup verification. Shared-workspace deletion has a separate operator-reviewed archived sole-owner/member workflow; archive, cancellation and logout are not deletion. Paid-service closure and unused-period remedies require a reviewed operational process before paid launch.",
        "सत्यापित सुरक्षा, दुरुपयोग या कानूनी दायित्व के लिए आवश्यक होने पर पहुँच सीमित की जा सकती है; समीक्षा के लिए संचालक से संपर्क करें। जहाँ कानूनी और संभव हो, कारण तथा सुधार या रिकॉर्ड निकालने का उचित अवसर दें; जरूरी सुरक्षा कार्रवाई में देरी न करें। रिकॉर्ड निकालने की सुविधा केवल समर्थित रिकॉर्ड पर है; हर फाइल या प्रवेश सेटिंग मिलने की गारंटी नहीं। निचली योजना की सीमा से ऊपर होने पर नया रिकॉर्ड बनाना रुक सकता है; इससे पुराने रिकॉर्ड मिटने का प्रमाण नहीं मिलता। व्यक्तिगत खाता हटाने के लिए नया प्रमाणीकरण, साझा डेटा की सुरक्षा, प्रदाता के प्रमाण और बैकअप सत्यापन वाली अलग संचालक-समीक्षित प्रक्रिया है। साझा कार्यक्षेत्र हटाने की अलग संचालक-समीक्षित प्रक्रिया में पहले संग्रहण, अकेला स्वामी-सदस्य और भुगतान/प्रबंधन/डेटा रोक का समाधान जरूरी है। संग्रहण, रद्द करना और बाहर निकलना विलोपन नहीं। सशुल्क सेवा बंद करने और बची अवधि के उपाय की कार्यप्रणाली सशुल्क शुरुआत से पहले समीक्षा करनी होगी।",
    ),
    section(
        "rights",
        "Responsibilities and mandatory rights",
        "जिम्मेदारियाँ और अनिवार्य अधिकार",
        "Verify inputs and important outputs, maintain appropriate copies and use only authorized integrations. These responsibilities do not excuse fraud, wilful misconduct, operator negligence where liability cannot lawfully be excluded, or statutory consumer/data rights. No arbitrary liability cap, blanket indemnity, class-action waiver or compulsory arbitration is imposed in this draft. Any future limitation must be specifically reviewed for applicable law and service commitments.",
        "दी गई जानकारी और महत्वपूर्ण परिणाम जाँचें, उचित प्रतियाँ रखें और केवल अधिकृत जुड़ाव उपयोग करें। इन जिम्मेदारियों से धोखाधड़ी, जानबूझकर गलत काम, जहाँ कानूनी रूप से जिम्मेदारी हटाई नहीं जा सकती वहाँ संचालक की लापरवाही, या उपभोक्ता और डेटा के वैधानिक अधिकार समाप्त नहीं होते। मसौदे में मनमानी जिम्मेदारी सीमा, असीमित क्षतिपूर्ति, सामूहिक कार्रवाई छोड़ना या अनिवार्य मध्यस्थता नहीं थोपी गई है। भविष्य की सीमा की लागू कानून और सेवा वादों के अनुसार अलग समीक्षा होगी।",
    ),
    section(
        "complaints",
        "Complaints, law and privacy",
        "शिकायतें, कानून और गोपनीयता",
        "Use the public contact above for terms, service and billing complaints. If applicable Indian e-commerce grievance rules apply, acknowledge within 48 hours and redress within one month; this is a legal requirement to operationalize, not proof of a staffed live SLA. The privacy notice explains data handling separately. Mandatory consumer forums and legal remedies remain available; no exclusive city/court is invented. India's mandatory applicable law governs relevant Indian service obligations without displacing protections that cannot be excluded elsewhere. Recheck applicability and the 2026 e-commerce amendments scheduled for 1 January 2027 before publication. This document is not a legal-compliance certificate.",
        "शर्तों, सेवा और भुगतान की शिकायत ऊपर के सार्वजनिक संपर्क पर दें। जहाँ भारत के ई-वाणिज्य शिकायत नियम लागू हों, 48 घंटे में प्राप्ति स्वीकार और एक महीने में निवारण करना चाहिए; यह लागू की जाने वाली कानूनी जिम्मेदारी है, चालू कर्मचारियों वाली समयबद्ध सेवा का प्रमाण नहीं। गोपनीयता नीति में डेटा सँभालना अलग बताया है। अनिवार्य उपभोक्ता मंच और कानूनी उपाय उपलब्ध रहते हैं; किसी काल्पनिक शहर या अदालत को अकेला अधिकार नहीं दिया गया है। संबंधित भारतीय सेवा दायित्वों पर भारत का अनिवार्य लागू कानून रहता है और दूसरी जगह के न हटाए जा सकने वाले संरक्षण समाप्त नहीं होते। प्रकाशन से पहले लागू होने की स्थिति और 1 जनवरी 2027 के लिए निर्धारित 2026 के ई-वाणिज्य संशोधन फिर जाँचें। यह दस्तावेज़ कानूनी अनुपालन का प्रमाणपत्र नहीं है।",
    ),
]


def public_terms(settings: Settings) -> dict:
    # Billing package imports ORM models; keep it outside Settings bootstrap.
    from app.billing.pricing import PRICE_CATALOG

    published = settings.terms_published and not publication_blockers(settings)
    return {
        "version": VERSION,
        "reviewed_on": REVIEWED_ON,
        "status": "published" if published else "draft",
        "effective_date": settings.terms_effective_date if published else None,
        "operator": {
            "brand_name": settings.operator_brand_name,
            "legal_name": (settings.operator_legal_name or None)
            if settings.operator_identity_enabled
            else None,
            "entity_type": settings.operator_entity_type,
            "country_code": settings.operator_country_code,
        },
        "contact": {
            "name": settings.terms_contact_name or None,
            "email": settings.terms_contact_email or None,
            "address": settings.terms_contact_address or None,
            "phone": settings.terms_contact_phone or None,
            "designation": settings.terms_contact_designation or None,
            "website": settings.terms_public_website or None,
        },
        "commercial": {
            "refund_policy": {
                lang: getattr(settings, f"terms_refund_policy_{lang}") or None
                for lang in ("en", "hi")
            },
            "cancellation_policy": {
                lang: getattr(settings, f"terms_cancellation_policy_{lang}") or None
                for lang in ("en", "hi")
            },
            "live_payments": False,
            "automatic_paid_activation": False,
            "recurring_billing": False,
            "automated_refunds": False,
            "tax_display_mode": settings.billing_tax_display_mode,
            "prices": [
                {
                    "plan": p.plan.value,
                    "interval": p.interval.value,
                    "amount_minor": p.amount_minor,
                    "currency": p.currency,
                }
                for p in PRICE_CATALOG.values()
            ],
        },
        "sections": SECTIONS,
    }
