# DubaiProp AI — Master Project Plan
## AI-Powered Real Estate Analytics Platform for Dubai, UAE

**Document Version**: 1.0  
**Date**: 2026-04-30  
**Prepared By**: Senior Project Manager (AI Agency)  
**Classification**: Internal — Commercial in Confidence  

---

## 1. EXECUTIVE SUMMARY

DubaiProp AI is an AI-powered real estate analytics platform targeting the Dubai residential and commercial property market. The platform delivers AI property search, dynamic price prediction, market analytics dashboards, investment scoring, rental yield analysis, and community-level insights.

**Key Constraints & Context**:
- Regulatory: RERA (Real Estate Regulatory Agency), DLD (Dubai Land Department), DIFC compliance mandatory
- Languages: English + Arabic (bi-di UI, RTL support)
- Platform: Mobile-first responsive web + PWA, with native mobile apps (Phase 2)
- AI/ML Stack: Price forecasting, NLP semantic search, recommendation engine, computer vision for property image analysis
- Data Sources: DLD REST API (where licensed), RERA rental index, public listings aggregation, proprietary user behavior

**Target Launch**: Q1 2026 (9-month build from kickoff)  
**Initial Operating Market (IOM)**: Dubai residential (off-plan + secondary), expanding to commercial in Phase 2

---

## 2. PROJECT PHASES, MILESTONES & DEPENDENCIES

### Phase Overview Table

| Phase | Name | Duration | Start | End | Key Deliverable |
|-------|------|----------|-------|-----|-----------------|
| 0 | Foundation & Compliance | 6 wks | W1 | W6 | Legal entity, DLD/RERA engagement, data agreements |
| 1 | Discovery & Architecture | 4 wks | W3 | W6 | PRD, system architecture, data pipeline design |
| 2 | Core Platform Build | 12 wks | W7 | W18 | MVP with search, analytics, basic AI models |
| 3 | AI/ML Integration | 8 wks | W13 | W20 | Price prediction, NLP search, recommendations live |
| 4 | QA, Compliance & Hardening | 4 wks | W19 | W22 | Security audit, RERA compliance sign-off, penetration testing |
| 5 | Beta & Pilot | 4 wks | W23 | W26 | Closed beta with 3 brokerages, 500 users |
| 6 | Launch & GTM | 4 wks | W27 | W30 | Public launch, marketing blitz, onboarding |
| 7 | Post-Launch Optimization | Ongoing | W31+ | — | Iteration, new features, market expansion |

> **Note**: Phases 1–3 have intentional overlap (agile sprints). Phase 0 is pre-kickoff legal/commercial work.

### Detailed Phase Breakdown

#### Phase 0: Foundation & Compliance (Weeks 1–6)
**Objective**: Establish legal presence, secure data access, and build regulatory relationships before writing production code.

- **W1–W2**: UAE legal entity setup (Mainland vs. DIFC vs. DMCC trade license for software/AI activity)
- **W2–W3**: DLD REST API application & data licensing agreement negotiation
- **W3–W4**: RERA engagement — understand data publishing obligations and brokerage license implications
- **W4–W5**: Trademark registration (Dubai Ministry of Economy), domain/IP protection
- **W5–W6**: Banking setup (AED accounts), VAT registration (if applicable), initial contracts (employment, vendor)

**Milestone P0-M1**: Legal entity operational, trade license issued  
**Milestone P0-M2**: DLD data access agreement executed (or rejected with fallback plan)  
**Milestone P0-M3**: RERA compliance framework documented

**Dependencies**: None (pre-project). Blocked by: government processing times (uncontrollable).

---

#### Phase 1: Discovery & Architecture (Weeks 3–6)
**Objective**: Finalize requirements, design system architecture, and plan data pipelines.

- **W3–W4**: Stakeholder interviews (brokers, investors, developers, property managers)
- **W4–W5**: Competitive analysis (Bayut, Property Finder, Dubizzle, DXBInteract)
- **W5–W6**: System architecture (microservices vs. monolith decision), database schema, API design
- **W5–W6**: AI/ML architecture — model selection, training data sourcing, inference pipeline
- **W6**: PRD v1.0 signed off, technical specification document finalized

**Milestone P1-M1**: PRD & tech spec approved by all stakeholders  
**Milestone P1-M2**: Architecture Decision Records (ADRs) published  
**Milestone P1-M3**: UI/UX wireframes and design system approved

**Dependencies**: P0 legal entity (for contract signing), P0 DLD engagement (for data schema understanding).  
**Parallelizable with**: Phase 0 from W3 onward.

---

#### Phase 2: Core Platform Build (Weeks 7–18)
**Objective**: Build the MVP web platform with property search, analytics dashboards, user management, and admin tools.

**Sprint Breakdown (2-week sprints):**

| Sprint | Weeks | Focus |
|--------|-------|-------|
| S1 | W7–W8 | Project scaffolding, CI/CD, dev environments, auth system |
| S2 | W9–W10 | Database implementation, property data ingestion pipeline, basic REST API |
| S3 | W11–W12 | Property search (filters, geo-search, pagination), listing detail pages |
| S4 | W13–W14 | User dashboards (saved searches, favorites, alerts), admin panel v1 |
| S5 | W15–W16 | Market analytics charts (price trends, transaction volume, area comparisons) |
| S6 | W17–W18 | Arabic RTL localization, PWA setup, performance optimization, Stripe integration |

**Milestone P2-M1**: Search & browse functional (internal demo) — W10  
**Milestone P2-M2**: Analytics dashboards live with real data — W16  
**Milestone P2-M3**: MVP feature-complete, Arabic support merged — W18

**Dependencies**: P1 architecture & PRD. Data ingestion blocked by DLD API or fallback scraper.  
**Critical Path Item**: Property data pipeline (no data = no platform).

---

#### Phase 3: AI/ML Integration (Weeks 13–20)
**Objective**: Integrate AI features into the live platform. Runs in parallel with S4–S6 of Phase 2.

- **W13–W14**: Price prediction model v1 (XGBoost/LightGBM baseline) — train on DLD transaction history
- **W15–W16**: NLP semantic search (embeddings + vector DB: Pinecone/Weaviate) — "3 bed villa near beach under 2M"
- **W17–W18**: Recommendation engine (collaborative + content-based filtering)
- **W19–W20**: Computer vision pipeline (property image classification, amenity detection, quality scoring)
- **W19–W20**: Investment scoring algorithm + rental yield calculator

**Milestone P3-M1**: Price prediction API live with 85%+ directional accuracy — W16  
**Milestone P3-M2**: NLP search deployed to production — W18  
**Milestone P3-M3**: All AI features integrated, A/B testing framework active — W20

**Dependencies**: P2 data pipeline (needs clean structured data). ML training blocked by data volume.  
**Critical Path Item**: Model training data quality and volume.

---

#### Phase 4: QA, Compliance & Hardening (Weeks 19–22)
**Objective**: Platform security, performance, and regulatory compliance before external exposure.

- **W19–W20**: Automated test coverage push (target: 80%+ unit, 60%+ integration)
- **W20–W21**: External penetration test (OWASP Top 10, API security)
- **W21**: RERA compliance review — advertising rules, broker license verification display, data accuracy obligations
- **W21–W22**: Load testing (simulate 10k concurrent users), CDN optimization
- **W22**: Bug bash, documentation, runbooks for on-call

**Milestone P4-M1**: Security audit passed, critical vulnerabilities resolved — W21  
**Milestone P4-M2**: RERA compliance checklist signed off by legal — W22  
**Milestone P4-M3**: Platform stable, monitoring & alerting production-ready — W22

**Dependencies**: P2 MVP complete, P3 AI features integrated.  
**Critical Path Item**: RERA compliance sign-off (external dependency).

---

#### Phase 5: Beta & Pilot (Weeks 23–26)
**Objective**: Controlled release to gather feedback and validate product-market fit.

- **W23**: Deploy to staging with production data mirror
- **W23–W24**: Onboard 3 partner brokerages (10 agents each) + 50 individual investors
- **W24–W25**: Feedback collection, analytics review, bug triage
- **W25–W26**: Iteration sprint — top 10 user requests addressed
- **W26**: Beta retrospective, go/no-go decision for public launch

**Milestone P5-M1**: 500 beta users active, >40% weekly retention — W26  
**Milestone P5-M2**: NPS score ≥ 30 from beta cohort — W26  
**Milestone P5-M3**: Go/no-go decision documented — W26

**Dependencies**: P4 compliance & hardening complete.

---

#### Phase 6: Launch & Go-to-Market (Weeks 27–30)
**Objective**: Public launch with coordinated marketing and sales.

- **W27**: Production deployment, app store submissions (if native apps ready)
- **W27–W28**: PR push (TechCrunch, Wamda, Gulf News tech section), influencer partnerships
- **W28–W29**: Paid acquisition campaigns (Google, Meta, LinkedIn), SEO content blitz
- **W29–W30**: Brokerage partnership onboarding (target: 20 signed)
- **W30**: Launch event (physical or virtual) — Dubai tech community

**Milestone P6-M1**: Platform publicly accessible, 1,000 registered users — W28  
**Milestone P6-M2**: 20 brokerage partnerships signed — W30  
**Milestone P6-M3**: MRR target: AED 50,000 — W30

**Dependencies**: P5 go decision. Marketing budget released.

---

### Dependency Graph (Critical Path)

```
[Phase 0: Legal/Compliance] ──► [Phase 1: Architecture] ──► [Phase 2: Core Build]
       │                              │                         │
       │                              ▼                         ▼
       │                    [Design System]          [Data Pipeline] ──► [Phase 3: AI/ML]
       │                                                         │            │
       ▼                                                         ▼            ▼
[DLD Data Agreement] ─────────────────────────────────────► [Phase 4: QA/Compliance]
                                                                   │
                                                                   ▼
                                                          [Phase 5: Beta]
                                                                   │
                                                                   ▼
                                                          [Phase 6: Launch/GTM]
```

**Critical Path**: Phase 0 (DLD agreement) → Phase 1 → Phase 2 (data pipeline) → Phase 3 → Phase 4 → Phase 5 → Phase 6

**Float Exists In**: Design system (can lag 2 weeks), computer vision model (can ship post-launch).

---

## 3. RESOURCE ALLOCATION PLAN

### Human Team Structure

| Role | Count | FTE | Phase Engagement | Location | Monthly Cost (AED) |
|------|-------|-----|------------------|----------|-------------------|
| **Leadership** |
| Product Manager / Project Lead | 1 | 1.0 | All phases | Dubai | 45,000 |
| CTO / Technical Architect | 1 | 1.0 | All phases | Dubai / Remote | 55,000 |
| **Engineering** |
| Senior Full-Stack Engineers | 2 | 2.0 | P1–P7 | Remote / Dubai | 35,000 × 2 |
| Backend Engineer (Data/ML) | 1 | 1.0 | P1–P7 | Remote | 30,000 |
| Frontend Engineer (Flutter/React) | 1 | 1.0 | P1–P7 | Remote | 28,000 |
| DevOps / SRE Engineer | 1 | 0.5 | P2–P7 | Remote | 25,000 |
| QA Engineer | 1 | 0.75 | P2–P7 | Remote | 18,000 |
| **AI/ML** |
| ML Engineer | 1 | 1.0 | P1–P7 | Remote / Dubai | 40,000 |
| Data Engineer | 1 | 0.75 | P1–P5 | Remote | 28,000 |
| **Design & UX** |
| Product Designer (UI/UX) | 1 | 0.75 | P1–P6 | Remote / Dubai | 22,000 |
| **Business** |
| Legal / Compliance Lead | 1 | 0.25 | P0, P4 | Dubai (local) | 20,000 |
| Marketing Manager | 1 | 0.5 | P5–P7 | Dubai | 25,000 |
| Business Development (Broker partnerships) | 1 | 0.5 | P5–P7 | Dubai | 25,000 |
| **Support** |
| Customer Success / Support | 1 | 0.5 | P5–P7 | Dubai | 15,000 |

**Total Human Team Size**: 14 people  
**Total Monthly Human Burn**: ~AED 426,000  
**9-Month Human Cost (Build Phase)**: ~AED 3,834,000

---

### AI Agent Swarm Assignments

| Agent Role | Assignment | Tools Used | Output |
|------------|-----------|------------|--------|
| **DevAgent-01** | Backend API development (Laravel/Node), database design | GitHub, CI/CD, SQL | REST API endpoints, migrations, seeders |
| **DevAgent-02** | Frontend implementation (React/Next.js + Tailwind), RTL Arabic support | GitHub, Figma, Storybook | Component library, page implementations |
| **MLAgent-01** | Price prediction model training, feature engineering | Python, scikit-learn, XGBoost, AWS SageMaker | Trained models, inference API, feature pipelines |
| **MLAgent-02** | NLP search + recommendation engine | Python, HuggingFace, Pinecone, FastAPI | Embedding service, semantic search API, rec system |
| **MLAgent-03** | Computer vision pipeline for property images | Python, PyTorch, OpenCV, AWS Rekognition | Image classification, amenity detection, quality scoring |
| **DataAgent-01** | Data ingestion, cleaning, ETL pipelines | Python, Airflow, PostgreSQL, S3 | Clean datasets, scheduled pipelines, data quality monitors |
| **SecAgent-01** | Security audits, dependency scanning, secret detection | TruffleHog, OWASP ZAP, SonarQube | Security reports, remediation tickets |
| **QAAgent-01** | Automated test generation, Playwright E2E tests | Playwright, Jest, PHPUnit | Test suites, QA screenshots, coverage reports |
| **PMAgent-01** | (This agent) Project tracking, documentation, stakeholder reporting | Markdown, Notion, Jira | Status reports, risk updates, milestone tracking |
| **ContentAgent-01** | SEO content generation, bilingual copy (EN/AR) | GPT-4, DeepL, custom prompts | Blog posts, listing descriptions, marketing copy |
| **BizDevAgent-01** | Lead qualification, outreach drafting, CRM automation | HubSpot, LinkedIn Sales Nav, Nowhere AI | Qualified lead lists, outreach sequences, pipeline reports |

**AI Swarm Infrastructure**:  
- GitHub Actions for CI/CD (automated builds on every push)  
- AWS/GCP compute for model training (spot instances to save cost)  
- Shared vector database (Pinecone/Weaviate) for NLP + rec systems  
- Centralized logging (Datadog / Grafana Cloud) for all agents

---

## 4. RISK REGISTER

| ID | Risk | Probability | Impact | Risk Score | Mitigation Strategy | Owner |
|----|------|------------|--------|-----------|---------------------|-------|
| R01 | **DLD denies or delays REST API access** | High | Critical | 15 | Build robust fallback scraper (respecting robots.txt, rate limits); partner with licensed broker for data sharing; budget for commercial data provider (e.g., REIDIN) | CTO |
| R02 | **RERA compliance changes or ambiguous interpretation** | Medium | Critical | 10 | Hire local real estate lawyer with RERA experience; build compliance-first (advertising rules, broker verification); maintain modular architecture for rapid changes | Legal Lead |
| R03 | **AI model accuracy below threshold (price prediction <75%)** | Medium | High | 8 | Start with interpretable models (XGBoost) before deep learning; ensemble multiple models; set user expectations with confidence intervals; human-in-the-loop validation | ML Lead |
| R04 | **Data quality issues (incomplete listings, stale prices)** | High | High | 12 | Multi-source validation (DLD + listings + user reports); freshness scoring; flag stale data; automated data refresh pipelines | Data Engineer |
| R05 | **Competitive response from Bayut/Property Finder** | Medium | Medium | 6 | Differentiate on AI/analytics (not listings volume); target investor segment first; build proprietary data moat (investment scores, yield analysis) | Product Manager |
| R06 | **Arabic NLP/RTL implementation complexity** | Medium | Medium | 6 | Use established RTL frameworks (Tailwind RTL plugin); hire native Arabic QA; test with real users early; support both formal and dialect Arabic where relevant | Frontend Lead |
| R07 | **Cybersecurity breach or data leak** | Low | Critical | 5 | Penetration testing before launch; encryption at rest and in transit; least-privilege access; regular audits; UAE data residency compliance (some data must stay in-country) | Security Agent |
| R08 | **Key talent departure during build** | Medium | High | 8 | Document everything (ADRs, runbooks); no single points of failure; competitive packages; remote-friendly culture; knowledge-sharing sessions | CTO |
| R09 | **Market downturn reduces real estate activity** | Low | High | 4 | Build tools valuable in downturns (investment scoring, distressed property alerts); diversify to rental market; reduce burn if needed | Product Manager |
| R10 | **Payment gateway / VAT compliance issues** | Medium | Medium | 6 | Use Stripe UAE (or Telr/Checkout.com); engage UAE tax consultant; implement VAT from day one even if below threshold | CFO / Legal |
| R11 | **User acquisition cost (CAC) too high in Dubai** | Medium | High | 8 | Focus on B2B2C (brokerage partnerships) for organic distribution; content SEO; referral programs; LinkedIn organic for investor segment | Marketing Manager |
| R12 | **Computer vision models fail on Dubai architecture styles** | Medium | Medium | 6 | Curate local training dataset; start with pre-trained models (ImageNet) + fine-tuning; set fallback to manual tagging; deprioritize if accuracy low | ML Lead |

**Risk Heat Map Summary**:
- **Red (Immediate Action)**: R01, R02, R04
- **Yellow (Monitor Closely)**: R03, R08, R11
- **Green (Accept/Track)**: R05, R06, R07, R09, R10, R12

---

## 5. BUDGET ESTIMATE (AED)

### 5.1 Development Costs (Months 1–9)

| Category | Amount (AED) | Notes |
|----------|-------------|-------|
| Human Resources (salaries + benefits) | 3,834,000 | 14 people, weighted FTEs, 9 months |
| Contractor / Freelancer buffer | 200,000 | Design spikes, legal review, security audit |
| **Subtotal Development** | **4,034,000** | |

### 5.2 Infrastructure & Tools (Annual, prorated for 9 months)

| Category | Amount (AED) | Notes |
|----------|-------------|-------|
| Cloud Infrastructure (AWS/GCP) | 180,000 | Compute, storage, CDN, databases, 9 months |
| AI/ML Infrastructure | 120,000 | GPU instances (SageMaker), vector DB, model hosting |
| DevTools & SaaS | 45,000 | GitHub, Figma, Notion, Datadog, Sentry, etc. |
| Data Licensing | 150,000 | DLD API (if paid), REIDIN fallback, other providers |
| **Subtotal Infrastructure** | **495,000** | |

### 5.3 Compliance & Legal

| Category | Amount (AED) | Notes |
|----------|-------------|-------|
| Legal entity setup (license, visas, office) | 80,000 | Trade license, establishment card, 3 visas |
| Legal retainers & compliance review | 60,000 | RERA specialist, data protection, terms of service |
| Penetration testing & security audit | 40,000 | External firm, OWASP + API testing |
| Trademark & IP protection | 15,000 | UAE trademark, domain protection |
| **Subtotal Compliance** | **195,000** | |

### 5.4 Marketing & Go-to-Market (Months 7–9)

| Category | Amount (AED) | Notes |
|----------|-------------|-------|
| Paid digital advertising | 200,000 | Google Ads, Meta, LinkedIn (3 months blitz) |
| Content production (EN + AR) | 50,000 | Blog, video, social media, PR |
| Launch event | 30,000 | Venue, catering, media, invitations |
| Influencer / Partnership deals | 40,000 | Real estate influencers, tech bloggers |
| SEO tools & agency support | 20,000 | Ahrefs, content agency retainer |
| **Subtotal Marketing** | **340,000** | |

### 5.5 Operations & Buffer

| Category | Amount (AED) | Notes |
|----------|-------------|-------|
| Office / Coworking | 36,000 | 9 months, Dubai flexible space |
| Travel & meetings | 20,000 | Partner meetings, RERA visits, events |
| Contingency (10% buffer) | 512,000 | Applied to total above |
| **Subtotal Operations** | **568,000** | |

### Total Budget Summary

| Phase | Amount (AED) |
|-------|-------------|
| Development | 4,034,000 |
| Infrastructure & Tools | 495,000 |
| Compliance & Legal | 195,000 |
| Marketing & GTM | 340,000 |
| Operations & Buffer | 568,000 |
| **TOTAL PROJECT BUDGET** | **5,632,000** |

**Rounded: ~AED 5.6 million (~USD 1.53 million)** for 9-month build + launch.

**Monthly Burn Rate**: ~AED 520,000 (including all categories prorated).  
**Post-Launch Runway**: Recommend raising for 12 months post-launch = additional AED 3M buffer.

---

## 6. GO-TO-MARKET TIMELINE & CRITICAL PATH

### GTM Timeline (Detailed)

```
Month 1-2  [FOUNDATION]
  ├─ Legal entity, banking, visas
  ├─ DLD API application submitted
  ├─ RERA initial engagement
  └─ Team hiring (core 5 people)

Month 3-4  [DISCOVERY & ARCHITECTURE]
  ├─ PRD finalized, ADRs published
  ├─ UI/UX design system (EN + AR)
  ├─ Data pipeline architecture
  └─ AI model baseline experiments

Month 5-6  [CORE BUILD - ALPHA]
  ├─ Auth, database, API foundation
  ├─ Property search & detail pages
  ├─ Data ingestion pipeline live
  └─ Basic analytics charts

Month 7-8  [AI INTEGRATION & BETA PREP]
  ├─ Price prediction API
  ├─ NLP semantic search
  ├─ Recommendation engine
  ├─ Arabic RTL full implementation
  └─ Security audit initiated

Month 9    [BETA LAUNCH]
  ├─ 3 brokerage partners onboarded
  ├─ 500 beta users
  ├─ Feedback loop active
  └─ Iteration sprint

Month 10   [PUBLIC LAUNCH]
  ├─ Production deployment
  ├─ Marketing campaign live
  ├─ PR push
  └─ First revenue
```

### Critical Path Analysis

**Critical Path Activities** (any delay pushes launch):
1. DLD data access agreement execution (Week 2–6) — *external dependency*
2. Property data pipeline operational (Week 9–12) — *technical foundation*
3. Price prediction model trained & deployed (Week 13–16) — *core value prop*
4. RERA compliance sign-off (Week 21–22) — *regulatory gate*
5. Beta go/no-go decision (Week 26) — *product-market fit validation*

**Critical Path Duration**: 26 weeks (6.5 months) from data agreement to beta.  
**Total Project Duration**: 30 weeks (7.5 months) from kickoff to public launch.

**Float Analysis**:
- Design system refinements: 2 weeks float
- Computer vision features: 4 weeks float (can ship post-launch)
- Advanced analytics (commercial property): 6 weeks float (Phase 2)
- Native mobile apps: 8 weeks float (Phase 2)

**Crash Options** (if schedule compression needed):
- Add second backend engineer: saves 2 weeks on API development (cost: +AED 210,000)
- Use managed ML services (AWS SageMaker Autopilot): saves 1 week on model baseline (cost: +AED 30,000)
- Parallelize beta onboarding with QA hardening: saves 1 week (risk: higher defect rate)

---

## 7. STAKEHOLDER MAP — DUBAI REAL ESTATE ECOSYSTEM

### Stakeholder Matrix

| Stakeholder | Role | Influence | Interest | Engagement Strategy |
|-------------|------|-----------|----------|---------------------|
| **Regulatory** |
| RERA (Real Estate Regulatory Agency) | Regulator | High | Medium | Proactive engagement, compliance-first approach, quarterly updates |
| DLD (Dubai Land Department) | Data owner / Regulator | High | Medium | Formal data partnership request, revenue-share discussion |
| DIFC Authority | If operating in DIFC | Medium | Low | Legal compliance only unless DIFC entity chosen |
| **Market Incumbents** |
| Bayut (Emerging Markets Property Group) | Major portal | High | Low | Monitor, differentiate on AI; potential partnership for data |
| Property Finder | Major portal | High | Low | Competitive intelligence; avoid direct feature parity |
| Dubizzle (an OLX company) | Classifieds / Listings | Medium | Low | Potential data scraping target (within legal bounds) |
| DXBInteract (DLD's own platform) | Official data portal | Medium | High | Complement, not compete; promote as enhanced UX layer |
| **Industry Players** |
| Large Brokerages (Betterhomes, Allsopp & Allsopp, etc.) | Customers / Partners | High | High | Early design partners, white-label potential, revenue share |
| Independent Agents | End users | Medium | High | Freemium tier, mobile-first tools, Arabic support |
| Property Developers (Emaar, DAMAC, etc.) | Data providers / Advertisers | Medium | Medium | API for new project launches, premium placement |
| Property Management Companies | B2B customers | Medium | High | Rental yield tools, portfolio analytics |
| **Investors & Users** |
| Retail Investors (local + expat) | Primary users | Medium | High | Investment scoring, community insights, Arabic support |
| Institutional Investors (REITs, family offices) | Enterprise prospects | High | Medium | Custom dashboards, API access, data exports |
| Expat renters / buyers | Secondary users | Low | High | Search experience, community guides, price transparency |
| **Technology & Services** |
| AWS / GCP / Azure | Cloud providers | Low | Low | Standard vendor management |
| Payment Gateways (Stripe UAE, Telr) | Infrastructure | Low | Low | Integration, compliance |
| Data Providers (REIDIN, CoreLogic) | Data partners | Medium | Medium | Fallback if DLD unavailable |
| **Community** |
| Dubai Tech Startups (in5, Astrolabs, Dtec) | Ecosystem | Low | Medium | Networking, hiring, potential accelerator |
| Government AI Office / Dubai Future Foundation | Innovation agenda | Medium | Medium | Position as AI innovation story for Dubai |

### Stakeholder Engagement Plan

**High Influence + High Interest (Key Players)**:
- Large Brokerages: Monthly steering committee, early access program, co-branded features
- RERA: Formal presentation before launch, compliance review, ongoing dialogue

**High Influence + Low Interest (Keep Satisfied)**:
- Bayut / Property Finder: Monitor public statements, avoid antagonistic PR, explore data partnerships
- DLD: Professional, formal engagement, respect data ownership

**Low Influence + High Interest (Keep Informed)**:
- End users (agents, investors): Regular product updates, feedback channels, community events
- Property management companies: Newsletter, webinars on product features

**Low Influence + Low Interest (Monitor)**:
- Cloud providers, general tech ecosystem: Standard vendor management, no special effort

---

## 8. SUCCESS METRICS & KPIs

### Product Metrics

| Metric | Target (Launch) | Target (6 Months Post-Launch) |
|--------|----------------|------------------------------|
| Monthly Active Users (MAU) | 2,000 | 15,000 |
| Property Searches / Month | 50,000 | 500,000 |
| Price Prediction API Calls | 10,000 | 100,000 |
| User Retention (Week 4) | 30% | 40% |
| NPS Score | ≥ 30 | ≥ 40 |

### Business Metrics

| Metric | Target (Launch) | Target (6 Months) |
|--------|----------------|-------------------|
| Monthly Recurring Revenue (MRR) | AED 50,000 | AED 300,000 |
| Paying Brokerages | 20 | 100 |
| Average Revenue Per Account (ARPA) | AED 2,500 | AED 3,000 |
| Customer Acquisition Cost (CAC) | < AED 500 | < AED 400 |
| Lifetime Value (LTV) | > AED 6,000 | > AED 9,000 |
| LTV:CAC Ratio | > 3:1 | > 4:1 |

### Technical Metrics

| Metric | Target |
|--------|--------|
| API Uptime | 99.9% |
| Page Load Time (p95) | < 2s |
| Price Prediction Latency (p95) | < 500ms |
| Model Accuracy (directional) | > 85% |
| Test Coverage | > 80% unit, > 60% integration |
| Security Vulnerabilities (critical) | 0 |

---

## 9. GOVERNANCE & REPORTING

### Sprint Cadence
- **2-week sprints** (aligned with Phase 2–3)
- Sprint Planning: Monday Week 1
- Daily Standups: 9:00 AM GST (15 min, async for remote)
- Sprint Review: Friday Week 2
- Retrospective: Friday Week 2 (30 min)

### Milestone Reviews
- Phase gates require formal sign-off from Product Manager + CTO
- RISK: Go/no-go decisions at P4 (compliance), P5 (beta), P6 (launch)
- Board/investor updates monthly (written) + quarterly (live)

### Tools Stack
- **Project Management**: Jira / Linear
- **Documentation**: Notion (wiki), Confluence (technical)
- **Communication**: Slack (async), Zoom (meetings)
- **Design**: Figma
- **Code**: GitHub (repos, actions, projects)
- **Analytics**: Amplitude / Mixpanel (product), Google Analytics (marketing)
- **Finance**: QuickBooks / Xero

---

## 10. APPENDIX

### A. Technical Stack Recommendation

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend | Next.js 14 (App Router), React, TypeScript | SSR for SEO, large ecosystem, PWA support |
| Styling | Tailwind CSS + Tailwind RTL plugin | Rapid development, Arabic RTL native support |
| Backend API | Laravel 11 (PHP) + Livewire (admin) OR Node.js / NestJS | Team preference; Laravel strong in Dubai market |
| Database | PostgreSQL (primary), Redis (cache/sessions) | ACID compliance, GIS extensions for geo-search |
| Vector DB | Pinecone or Weaviate | Semantic search, recommendation embeddings |
| AI/ML | Python, FastAPI, scikit-learn, XGBoost, PyTorch | Standard ML stack, good model serving |
| Cloud | AWS (primary), GCP (ML backup) | AWS dominant in UAE, local region (me-south-1) |
| DevOps | GitHub Actions, Docker, Kubernetes (EKS) | Scalable, industry standard |
| Monitoring | Datadog, Sentry, PagerDuty | Full-stack observability |

### B. Arabic Localization Requirements

- Full RTL layout (Tailwind RTL)
- Arabic numerals vs. Eastern Arabic numerals (user preference)
- Hijri calendar option for rental/lease dates
- Bi-di text support (mixed EN/AR content)
- Right-aligned charts and data visualizations
- Arabic search normalization ( tashkeel removal, alef variants )
- Legal documents in Arabic (RERA requirement)

### C. Regulatory Checklist (RERA / DLD)

- [ ] Broker license numbers displayed on all listing pages (if showing agent info)
- [ ] Advertised prices match DLD records (or flagged as estimate)
- [ ] No misleading property descriptions (AI-generated content needs disclaimer)
- [ ] Data privacy compliance (UAE PDPL — Personal Data Protection Law)
- [ ] Terms of Service and Privacy Policy in Arabic
- [ ] Escrow account information displayed for off-plan projects
- [ ] RERA registration number for platform (if required for advertising)
- [ ] DLD-approved rental calculator integration (if offering rental valuations)

---

*End of Document*
