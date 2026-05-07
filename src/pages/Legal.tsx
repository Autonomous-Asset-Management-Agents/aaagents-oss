/**
 * Legal page drafts — Imprint (§ 5 TMG), Privacy (GDPR/DSGVO Art. 13/14),
 * Risk Disclosure.
 *
 * These are launch-ready DRAFTS based on publicly available AAAgents facts
 * (entity, contact, processors, scope). They have NOT been reviewed by
 * counsel. Every field that must be verified by a lawyer or filled in
 * once the GmbH is registered is marked [to be confirmed]. Replace before
 * any production / live-trading deploy — BaFin, DSGVO and § 18 MStV
 * place real liability on the wording here.
 *
 * See docs/6_runbooks/OPERATIONS_REFERENCE.md for the "publish → monitor"
 * sign-off flow.
 */
import { useNavigate } from "react-router-dom";
import "@/styles/landing-b.css";

interface LegalPageProps {
    kind: "imprint" | "privacy" | "risk-disclosure";
}

const LAST_UPDATED = "2026-04-23";
const ENTITY = "AAAgents GmbH (in Gründung)";
const ADDR_STREET = "[Street + house number — to be confirmed once GmbH is registered]";
const ADDR_CITY = "[Postcode + city — to be confirmed]";
const ADDR_COUNTRY = "Germany";
const CONTACT_EMAIL_GENERAL = "info@aaagents.de";
const CONTACT_EMAIL_PRIVACY = "privacy@aaagents.de";
const CONTACT_EMAIL_SECURITY = "security@aaagents.de";
const REPRESENTATIVES = "Georg Apeldorn, Andreas Apeldorn (Geschäftsführer)";

const CONTENT: Record<LegalPageProps["kind"], { title: string; body: string }> = {
    imprint: {
        title: "Imprint",
        body: `Information according to § 5 TMG and § 18 (2) MStV.


1. Provider

${ENTITY}
${ADDR_STREET}
${ADDR_CITY}
${ADDR_COUNTRY}

Represented by the managing directors: ${REPRESENTATIVES}

While the GmbH is being formed ("i.Gr."), the acting partners are
personally responsible within the meaning of § 11 (2) GmbHG. Once the
entity is registered in the commercial register, this page will be
updated with the full HRB entry and responsibility will transfer to
the GmbH by operation of law.


2. Contact

Email:     ${CONTACT_EMAIL_GENERAL}
Security:  ${CONTACT_EMAIL_SECURITY}   (vulnerability reports, PGP on request)
Privacy:   ${CONTACT_EMAIL_PRIVACY}   (data-subject requests)

Telephone: [to be confirmed once a business line is provisioned]


3. Register and tax information

Commercial register:   [HRB number — pending registration]
Registration court:    [Amtsgericht — to be confirmed]
VAT ID (USt-IdNr.):    [DE… — pending tax-office assignment]
Business tax number:   [Steuernummer — pending]


4. Regulatory status

AAAgents is currently operated as a demonstration and paper-trading
platform. No investment services within the meaning of § 2 (1) WpIG /
MiFID II Annex I, Section A, are offered to the public at this stage.
No client securities or client funds are held.

Authorisation by the Federal Financial Supervisory Authority (BaFin)
pursuant to § 15 WpIG for the provision of investment services, and
the corresponding DORA and MiFID II operational obligations, are in
preparation. No public offering within the meaning of § 2 (1) WpPG
has been made and no prospectus approved by BaFin exists. Until
authorisation is granted, content on this site must not be construed
as an offer, solicitation, investment advice or placement of financial
instruments.


5. Editorially responsible (§ 18 (2) MStV)

Georg Apeldorn, c/o ${ENTITY}, address as above.


6. EU dispute resolution and consumer arbitration

The European Commission provides a platform for online dispute
resolution (OS):  https://ec.europa.eu/consumers/odr

We are neither willing nor obliged to participate in dispute
resolution proceedings before a consumer arbitration board
(Verbraucherschlichtungsstelle) within the meaning of § 36 VSBG.


7. Liability for content

Pursuant to § 7 (1) TMG we are responsible for our own content on
these pages under the general laws. Under §§ 8–10 TMG, however, we
are not obliged to monitor third-party information transmitted or
stored, nor to investigate circumstances indicating illegal activity.
Obligations to remove or block the use of information under the
general laws remain unaffected; such liability arises only upon
knowledge of a specific infringement and will be addressed without
delay.


8. Liability for links

Our site contains links to external third-party websites over whose
content we have no control. Therefore we cannot assume any liability
for this external content. Responsibility for the content of the
linked pages lies exclusively with the respective provider or
operator. The linked pages were checked for possible legal
infringements at the time of linking; no illegal content was apparent
at that time. A permanent review of linked pages is not reasonable
without specific evidence of an infringement. Upon notification of
infringements, such links will be removed immediately.


9. Copyright

Content and works on these pages produced by the site operators are
subject to German copyright law. Reproduction, processing,
distribution and any form of commercialisation of such material
beyond the scope of the copyright law require the prior written
consent of the respective author or creator. Downloads and copies of
this site are permitted only for private, non-commercial use. Where
content on this site was not created by the operator, the copyrights
of third parties are respected and third-party content is marked as
such. Should you nonetheless become aware of a copyright
infringement, please notify us and we will remove the content
immediately.


Last updated: ${LAST_UPDATED}
Draft status: pending counsel review. Errors are ours to correct,
not to rely on.`,
    },
    privacy: {
        title: "Privacy Policy",
        body: `This privacy policy explains how AAAgents processes personal data
in accordance with Regulation (EU) 2016/679 (GDPR / DSGVO), the
Federal Data Protection Act (BDSG) and the Telecommunications-
Telemedia Data Protection Act (TTDSG). It fulfils the information
duties under Art. 13 and Art. 14 GDPR.


1. Controller (Art. 4 No. 7 GDPR)

${ENTITY}
${ADDR_STREET}
${ADDR_CITY}
${ADDR_COUNTRY}

Email: ${CONTACT_EMAIL_PRIVACY}

The controller is represented by the acting partners during formation
(see Imprint). A data protection officer is not mandatory at the
current scale under § 38 (1) BDSG; contact on privacy matters is
handled via ${CONTACT_EMAIL_PRIVACY}.


2. Categories of personal data processed

(a) Waitlist (landing page): email address, timestamp and user-agent
    string. Collected only when you actively submit the form.
(b) Authenticated console: email address, Google OAuth identifier,
    session tokens issued by Firebase Authentication.
(c) Operator audit log: actions you perform in the console (trade
    approvals, parameter changes) are logged with your identifier for
    compliance and auditability.
(d) Technical and security logs: IP address, timestamp, requested URL,
    response status, user-agent, referer.
(e) Analytics (only after consent): pseudonymous identifiers and
    page-view events via Google Analytics 4, with IP anonymisation.
    Analytics is loaded only after explicit opt-in per Google Consent
    Mode v2; without consent no analytics cookies are set.


3. Purposes and legal bases of processing

(a) Waitlist registration → Art. 6 (1) lit. b GDPR (pre-contractual
    measures on the data subject's request). Optional event-based
    notifications only after a further specific consent (Art. 6 (1)
    lit. a GDPR).
(b) Console access and operator identity → Art. 6 (1) lit. b GDPR
    (performance of the contract with the operator) and Art. 6 (1)
    lit. f GDPR (legitimate interest in access control for a
    regulated platform).
(c) Operator audit log → Art. 6 (1) lit. c GDPR (legal obligation;
    MiFID II record-keeping and, once authorised, §§ 63 ff. WpHG)
    and Art. 6 (1) lit. f GDPR (legitimate interest in investigable
    operational security).
(d) Technical / security logs → Art. 6 (1) lit. f GDPR (legitimate
    interest in operating a secure platform and defending against
    abuse). Balancing of interests has been performed and is
    documented internally.
(e) Analytics → Art. 6 (1) lit. a GDPR (consent) plus § 25 (1)
    TTDSG for storage / access on your device. Consent can be
    withdrawn at any time with effect for the future.


4. Recipients and processors (Art. 28 GDPR)

We use the following processors. Data processing agreements
pursuant to Art. 28 GDPR are in place with each.

• Google Ireland Ltd. (Firebase Authentication, Firestore, Remote
  Config, Hosting, App Check) — Dublin, Ireland. Data is processed
  within the EU; processors in the USA may access data under the
  EU-US Data Privacy Framework adequacy decision (C(2023) 4745).
• Google Ireland Ltd. (Google Cloud Run, region europe-west3) —
  Dublin, Ireland. Back-end hosting within the EU.
• Alpaca Securities LLC (paper and, later, live brokerage) — New
  York, USA. Transfer under Art. 46 (2) lit. c GDPR (Standard
  Contractual Clauses) and the EU-US Data Privacy Framework where
  applicable. Used only when you connect a broker account.
• Google reCAPTCHA v3 (App Check provider) — Google Ireland Ltd.;
  third-country component: Google LLC.

No sale, rental or transfer of personal data to third parties for
advertising purposes takes place.


5. Transfers to third countries

To the extent that processing involves a country outside the EU/EEA,
it is based on the EU-US Data Privacy Framework adequacy decision
(where applicable) or on Standard Contractual Clauses under Art. 46
(2) lit. c GDPR with additional technical and organisational
measures. You may request a copy of the relevant safeguards at
${CONTACT_EMAIL_PRIVACY}.


6. Storage periods

(a) Waitlist entries: until you request deletion, or at the latest
    24 months after the last signal of interest.
(b) Console data: for the duration of the operator relationship plus
    statutory retention (up to 10 years per § 257 HGB / § 147 AO
    once the platform is authorised for investment services and
    records are legally mandated).
(c) Operator audit log: 10 years after creation, in line with MiFID
    II record-keeping requirements.
(d) Technical / security logs: 14 days for routine access logs;
    longer only when needed to investigate a specific security
    incident, and only for as long as that purpose requires.
(e) Analytics: the retention period configured in GA4 (currently
    14 months), or earlier on your withdrawal of consent.


7. Your rights under GDPR

You have, with respect to the personal data we process about you,
the following rights:

• Information and access — Art. 15 GDPR
• Rectification — Art. 16 GDPR
• Erasure ("right to be forgotten") — Art. 17 GDPR
• Restriction of processing — Art. 18 GDPR
• Data portability — Art. 20 GDPR
• Objection against processing based on Art. 6 (1) lit. e or f GDPR
  — Art. 21 GDPR, including direct marketing at any time
• Withdrawal of consent with effect for the future — Art. 7 (3) GDPR
• Not to be subject to a decision based solely on automated
  processing that produces legal effects — Art. 22 GDPR (see
  section 8)

To exercise any of these rights, email ${CONTACT_EMAIL_PRIVACY}. We
will respond within one month pursuant to Art. 12 (3) GDPR.


8. Automated decision-making and profiling (Art. 22 GDPR)

AAAgents uses AI agents and statistical models to generate investment
recommendations. In the current demonstration / paper-trading phase
no real-money orders are executed automatically on your behalf.

Once real-money execution is authorised, automated recommendations
will be subject to explicit human approval for every capital-moving
action ("human-in-the-loop") in accordance with Art. 14 of the EU AI
Act. You will not be subject to any decision that is based solely on
automated processing and that produces legal effects concerning you
without an express separate contract and the safeguards required
under Art. 22 (2) and (4) GDPR.


9. Right to complain

Independent of any other administrative or judicial remedy, you have
the right to lodge a complaint with a supervisory authority, in
particular in the Member State of your habitual residence, place of
work or place of the alleged infringement, if you consider that the
processing of personal data relating to you infringes the GDPR
(Art. 77 GDPR).

The competent supervisory authority for AAAgents is the data
protection authority of the German federal state where our registered
office is located, to be identified once registration is complete.
A list of German DPAs is available at:
https://www.bfdi.bund.de/EN/Service/Anschriften/anschriften-node.html


10. Cookies and similar technologies

We use only strictly necessary cookies (authentication, session
state) without consent, on the basis of § 25 (2) no. 2 TTDSG. All
other cookies and storage accesses (analytics, A/B testing preference)
are set only after explicit opt-in, implemented via Google Consent
Mode v2 with analytics_storage denied by default.


11. Changes to this policy

We reserve the right to update this policy to reflect changes in
processing activities or in the law. The current version is always
available at https://aaagents.de/legal/privacy.


Last updated: ${LAST_UPDATED}
Draft status: pending counsel review. Specific data-processing
facts (retention periods, processors, transfer mechanisms) are
accurate to our current implementation; legal framing will be
finalised with counsel.`,
    },
    "risk-disclosure": {
        title: "Risk Disclosure",
        body: `IMPORTANT — CAPITAL-MARKET RISK WARNING. PLEASE READ CAREFULLY
BEFORE USING THIS PLATFORM OR ACTING ON ANY INFORMATION IT PROVIDES.


1. No investment advice, no offer

Content on this site, in the AAAgents console and in any generated
reports or recommendations is provided for information and
demonstration purposes only. It does not constitute investment
advice, investment placement, a personal recommendation, an offer to
buy or sell securities, or a solicitation to engage in any
transaction. No fiduciary, advisory or client relationship is
established by visiting this site or by engaging with the
demonstration platform.

Investment decisions require consideration of your individual
financial situation, investment objectives, risk tolerance and time
horizon. You should consult an independent, authorised investment
adviser, tax adviser and where appropriate a lawyer before making
any investment decisions.


2. General risk of capital loss

The value of investments can go down as well as up. You may not get
back the amount you originally invested, and you may lose the entire
invested capital. Past performance is not a reliable indicator of
future results. Simulated, hypothetical or backtested performance is
not an indicator of future or actual performance and has specific
limitations (see § 5 below).


3. Platform-specific risks

(a) Model and algorithm risk
    AAAgents relies on machine-learning models, statistical
    predictors and multi-agent consensus mechanisms. Models can be
    wrong, are trained on historical data that may not represent
    future regimes, and can fail silently in market regimes not
    represented in their training distribution. Consensus and
    guardrail layers (Investment Board voting, Compliance Guardian,
    cuFOLIO optimizer, Risk Manager) reduce but cannot eliminate
    these risks.

(b) Data risk
    Decisions are derived from market data, alternative data and
    news feeds obtained from third-party providers. Data latency,
    outages, stale values, incorrect symbols or corrupted ticks can
    lead to incorrect signals. Despite validation, defective input
    data can propagate to incorrect decisions.

(c) Execution and counterparty risk
    Orders, where executed, are routed via third-party brokers (e.g.
    Alpaca) and clearing infrastructure. Broker failures, order
    rejections, partial fills, slippage, outages and insolvencies of
    counterparties can cause losses or unintended positions.

(d) Liquidity risk
    Instruments that appear liquid may become difficult to trade at
    fair prices during stress, gap events, circuit-breaker halts or
    outside of regular trading hours. Strategies that are crowded
    can suffer accelerated losses during unwind.

(e) Concentration risk
    Portfolios may be concentrated in a small number of instruments,
    sectors or factors. Sizing caps in the optimizer mitigate but do
    not remove this exposure.

(f) Regulatory risk
    Changes in law, BaFin / ESMA guidance, MiFID II / DORA
    requirements, tax treatment or broker rules may materially
    affect the platform's strategies, their availability or their
    cost. The legal framework for AI-assisted investment services
    is evolving.

(g) Technology, operational and cyber risk
    Software bugs, infrastructure outages, network failures, denial-
    of-service attacks or intrusions may impair the platform's
    ability to produce correct signals or to execute intended
    actions. A documented kill-switch and drawdown-halt exist but
    cannot anticipate every failure mode.

(h) Model-drift and regime-change risk
    The accuracy of the underlying models is continuously monitored.
    Nevertheless, persistent drift can require model retraining and
    may cause a temporary degradation of signal quality.


4. Current status of AAAgents

AAAgents is currently operated as a demonstration and paper-trading
platform. No investment services within the meaning of § 2 (1) WpIG
/ MiFID II are offered to the public. No client securities or client
funds are held. Performance figures shown on this site reflect
simulated or paper-trading results and may be illustrative.

Real-money execution on behalf of users is offered only once
authorisation under § 15 WpIG has been granted by BaFin and the
corresponding MiFID II, DORA and GDPR controls have been audited.
Until then, any engagement is limited to the demonstration and
waiting-list purposes described in the Imprint.


5. Limitations of simulated performance

Simulated or paper-trading results do not reflect actual trading.
Because trades have not actually been executed, results may have
under- or over-compensated for the impact of certain market
factors including but not limited to real liquidity, venue
rejections, partial fills, adverse selection, market impact,
latency, financing costs, borrow availability, tax, fees and
commissions. In general simulated programs benefit from hindsight.
No representation is being made that any account will or is likely
to achieve profits or losses similar to those shown.


6. Suitability

The services and demonstrations made available through AAAgents are
not suitable for every investor. They presuppose an understanding of
equity, FX and derivative markets, of algorithmic trading and of AI-
based decision systems. You are responsible for assessing whether
the platform is appropriate for your circumstances.


7. No guarantee

No statement on this site, in the console or in any AAAgents
communication may be understood as a guarantee of returns, a
guarantee of risk management or a guarantee of any outcome. All
figures, rankings, agent votes and portfolio states are provided
without warranty of any kind.


Acknowledgement

By using this platform you acknowledge that you have read,
understood and accepted this risk disclosure.


Last updated: ${LAST_UPDATED}
Draft status: pending counsel review. Substance is intended to
reflect the current state of the platform; wording will be
finalised with counsel.`,
    },
};

export default function Legal({ kind }: LegalPageProps) {
    const navigate = useNavigate();
    const { title, body } = CONTENT[kind];
    return (
        <div className="landing-b-root">
            <nav className="lb-nav">
                <button className="lb-nav-logo" onClick={() => navigate("/")} style={{ background: "none", border: "none", cursor: "pointer" }}>
                    aaagents<span style={{ color: "#00c27a" }}>_</span>
                </button>
                <div className="lb-nav-right">
                    <button className="lb-nav-link" onClick={() => navigate("/")}>Home</button>
                    <button className="lb-nav-link" onClick={() => navigate("/live")}>Live</button>
                </div>
            </nav>
            <article className="lb-container" style={{ padding: "60px var(--lb-gutter) 120px", maxWidth: 820 }}>
                <div className="lb-eyebrow" style={{ fontFamily: "var(--lb-mono)", fontSize: 12, letterSpacing: 2.5, textTransform: "uppercase", color: "var(--lb-muted-light)", marginBottom: 16 }}>
                    Legal · Draft pending counsel review
                </div>
                <h1 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, lineHeight: 1, letterSpacing: "-0.02em", margin: "0 0 32px" }}>{title}</h1>
                <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--lb-font)", fontSize: 16, lineHeight: 1.7, color: "var(--lb-fg-light)", margin: 0 }}>
                    {body}
                </pre>
            </article>
        </div>
    );
}
