# Research Notes — 03_STUDENT_INFRA_REPORT_NOTES.md

> These notes are a structured extraction of the supplied report. The original PDF remains authoritative for exact wording, tables and citations.

## 1 Executive Summary

Student status in 2026 is still a genuine resource-acquisition mechanism, but the landscape
has changed sharply in the last six months. Two events dominate this audit: DigitalOcean
exited the GitHub Student Developer Pack entirely (its $200 student credit retired on
August 1, 2026), and GitHub suspended new sign-ups for the Copilot Student plan (since
April 20, 2026). Several other famous programs are dead too — the AWS Educate $100
grants, the standalone $50 Anthropic student API credit, and Cursor's and Windsurf's
student discounts were all discontinued in 2026. A "free credits list" from 2024 is now
dangerously misleading.
Within these constraints, a legitimate Indian student can still assemble a remarkably
capable stack at $0 personal cost. The verified core is: the GitHub Student Developer Pack
(still valuable despite the erosion — Azure $100, JetBrains Student, MongoDB $50, Sentry,
Clerk, Doppler, Heroku $13/mo for 24 months, New Relic, free domains), JetBrains Student
Pack (all professional IDEs free, renewable annually, verified via the GitHub pack), Google
Cloud education coupon grants (real billing credits with 1-year validity, but only
obtainable through a professor who applies for the course), Hugging Face, Groq,
Cerebras, Gemini free tiers (perpetual free LLM inference), free GPU compute (Kaggle ~30
hrs/week T4, Colab, Oracle Cloud Always Free with 4 OCPU ARM + 24 GB), and perpetual
free PaaS (Vercel Hobby, Netlify, Cloudflare Workers, Render, Supabase). India-specific
routes include Cloudflare's student plan (US-only — not available), so the realistic India
path is the general free plans plus university-incubator channels to AWS Activate, Google
for Startups, and DigitalOcean Hatch credits.
The $300 Azure credit is best treated as a finite conversion budget, not a permanent
server farm: roughly 575 hours of T4 GPU compute, ~3,600 hours of a 2-vCPU/4-GB
machine, or 4+ years of a small B1s VM — with the sobering caveats that Azure OpenAI is
excluded from student credits, and GPU quota on student subscriptions is frequently
 denied. The report's central recommendation: spend the credits on short, high-value
bursts (GPU fine-tuning experiments, one rea

[Section continues in full extracted source text.]

## 2 GitHub Student Developer Pack — Complete Audit

The pack was audited page-by-page (official education.github.com/pack) on August 9,
2026, across the Cloud, Infrastructure & APIs, Developer Tools, Domains, and Hosting
categories. Every offer below was verified against the official pack listing on that date; pack
contents change frequently, so treat the "verification date" as part of the record.
Eligibility mechanics first. The pack requires a verified student account (age 13+, enrolled
in a degree/diploma program) proven by a school-issued email address and/or official
dated proof of enrollment (student ID, transcript, tuition bill). Verification is re-evaluated
monthly [1]. Indian credentials (AICTE/UGC-recognized institution, .edu.in or ac.in email, or
student ID photo) are accepted — this was confirmed by India students in pack discussions
and by partner programs (JetBrains explicitly lists India among eligible countries). India
eligibility is therefore confirmed for the pack as a whole.
2.1 The anchor benefits (high value, use these)
 Offer           What you get Duration /       India             Card            Notes
                                renewal
                 Unlimited
                 private repos, Permanent
 GitHub Pro      protected      while verified Yes               No              Core of the
                 branches,      (monthly re-                                     pack
                 CODEOWNERS verification)
                 , advanced CI
 GitHub          3,000 CI       Permanent Yes                    No              Real CI/CD for
 Actions &       min/mo, 180 while verified                                      free
 Codespaces      Codespaces
                 hrs/mo, 20
             GB codespace
            storage, 2 GB
            Packages
            Access to 25+                              Excludes
            Azure            12 mo from                Azure OpenAI,
Microsoft   services +       creation; one Yes    No   Marketplace,
Azure       $100 credit,     subscription              DevOps paid
            12 months,       per customer              tiers, support
            no credit card                             [2]
            All 10
            professi

[Section continues in full extracted source text.]

## 3 Independent Student Programs (Beyond GitHub)

3.1 Cloud providers
Provider   Student      Amount       India        Card   Expiry       Verdict
           offer
                                                                    Confirmed
                                                                    — but note
                                                                    the user
                                                                    already has
                                                                    Azure
           Azure for    $100, 12    Yes (18+,                       credits;
Azure      Students     mo, no card SheerID  or   No     12 mo      this is the
                                    org email)                      same offer,
                                                                    one
                                                                    subscriptio
                                                                    n per
                                                                    customer
                                                                    [2]
                                                                    Confirmed
                                                                    but
           Google                                                   limited —
           Cloud for                                                these
Google     Students     $200         Yes          No     1 yr       credits are
Cloud      ("Google     credits                                     scoped to
           Skills")                                                 lab "skill
                                                                    boosts",
                                                                    not general
                                                                    billing [8]
                                                                    Real, but
                                                                    professor-
                                                                    gated: a
                                                                    faculty

[Section continues in full extracted source text.]

## 4 AI-Specific Student Programs

This section prioritizes actual API/compute value over productivity tools. The headline
finding: the era of blanket "AI credits for every student" is over in 2026, and what
remains is either regional, cohort-based, or researcher-gated.
 Program                Offer                    India eligible?          Status Aug 2026
 OpenAI Codex for       $100 ChatGPT credits     No — US & Canada         Active but region-
 Students               (2,500 credits), 12 mo   only [19]                restricted
 OpenAI Researcher      Up to $1,000 API         Yes (research proposal) Application review [20]
 Access                 credits / 12 mo
                        Cohort perks incl.                                Spring 2026 in session;
 Anthropic Claude       ~$50/mo API credits      No official country      applications closed;
 Campus                 reported                 block; cohort-based      next window ~fall
                                                                          2026 [21]
 Anthropic $50          (legacy standalone       —                        Dead — folded into
 student builder credit offer)                                            Claude Campus
 Anthropic External Free API credits for AI      Yes (research-based)     Application review
 Researcher             safety/alignment
                          researchers
                                                                          Discontinued Jun 25,
 Cursor student                                                           2026; graduate credits
 discount                50% off Pro              Yes                     only via form;
                                                                          undergrad offers via
                                                                          campus events [22]
                                                                          Discontinued Jun
 Windsurf student        50% off                  Yes                     2026; product
 discount                                                                 renamed to Devin
                                                                          Desktop [23]
           

[Section continues in full extracted source text.]

## 5 India-Specific Opportunities

Three India-specific routes verified as legitimate for an Indian university student. First,
Google Cloud education coupons — Indian institutions appear on Google's eligible-
institution list, and the mechanism (professor applies → coupons to students → 1-year
billing credits on all services) is explicitly global [9]. Action: ask your CS department or
 course instructor to apply at edu.google.com. Second, university incubation channels to
startup credit programs: Indian E-Cells, AICs (Atal Incubation Centres), T-Hub, and CIIE
regularly distribute AWS Activate credits (from $1,000 up, in tiers), Google for Startups
Cloud Program credits (up to $200K, $350K for AI startups), Microsoft for Startups, and
DigitalOcean Hatch credits to student ventures that incorporate or register a legitimate
project [26] [27]. Third, government-linked initiatives: the Startup India ecosystem
distributes partner cloud credits through its incubator network; a student-founded venture
registering under Startup India can legitimately access these tiers. These are startup
eligibility paths, not student paths — they require a genuine venture or incubator
relationship, which is exactly what the rules permit, not what they forbid.
Cloudflare's student plan, OpenAI Codex for Students, v0 for Students, and Thunder
Compute are confirmed unavailable in India and should be ignored.

## 6 The $300 Azure Problem — Utilization Strategy

6.1 What the credits can and cannot buy
Azure for Students credits are excluded from Azure OpenAI, Marketplace third-party
software, paid DevOps services, ExpressRoute, and support plans [2]. Azure AI Foundry pay-
as-you-go model inference (GPT, Claude, Llama, open models via the platform) is usable on
student subscriptions in most configurations, and core IaaS/PaaS is fully usable. GPU VM
quota is the hidden trap: student subscriptions frequently have zero approved GPU quota,
and raising it is approval-based. Before planning any GPU spend, check quota in the
Azure portal (Subscription → Usage + quotas → GPUs) — do this in week one.
6.2 Conversion math (Central India region, Aug 2026 prices)
 Resource                 Unit cost            $300 buys              Equivalent
 B1s burstable VM (1      $0.0112/hr ≈ $8.2/mo ~3,600 hrs → ~4+       Small dev server
 vCPU, 1 GB)                                   years continuous
 B2s burstable VM (2      $0.043/hr ≈ $31/mo ~900   hrs → ~12.5 mo    Real app server
 vCPU, 4 GB)                                   continuous
 D2as v5 (2 vCPU, 8 GB)   ~$0.09/hr ≈ $65/mo ~3,300 hrs → ~4.5 mo    Staging/ML prep server
 T4 GPU VM                ~$0.52/hr            ~575 GPU-hours        Fine-tuning LoRAs,
 (NC4as_T4_v3)                                                       eval runs
 Spot VMs (same           −40–70%              up to ~2.5× the above Interruptible batch
 classes)                                                            work
  PostgreSQL Flexible    $0.07/hr ≈ $51/mo       ~6 mo                  Managed DB
 Server (Basic 1vCPU)
 Container Apps (0.5    ~$0.012/hr ≈ $8.6/mo ~35 mo                    App hosting w/
 vCPU profile)                                                         autoscale
 Blob LRS storage       $0.016/GB/mo            ~18 TB-year            Practically unlimited
 Azure Functions        pay-per-execution       thousands of           Event-driven glue
 Consumption                                    executions


6.3 Recommended allocation (the strategy)
Treat the $300 as a project-funding tranche, deployed in three buckets. Bucket A —
durable production spine (~$120–150): one B2s-class VM or Con

[Section continues in full extracted source text.]

## 7 Production Infrastructure Strategy — Is It Sensible?

The architecture in the brief (internet → reverse proxy → app server + API server →
database → storage, plus cloud or self-hosted inference) is economically sensible at small
scale on the $0 + credits combination, but not as a pure-Azure build. At $0 you get a
genuinely close approximation: Cloudflare as reverse proxy/CDN/WAF, Vercel (frontend) and
a free Render/Cloudflare Workers instance (API), Supabase or Neon free Postgres
(database), Cloudflare R2/Azure Blob (storage), and external LLM APIs (inference). The Azure
credits then fund the one layer free tiers cannot provide: persistent, always-on, non-
sleeping compute — a B2s VM at ~$31/mo for 3+ months covers the exact gap (always-on
worker, webhook receivers, agents, Cron jobs) during your most active building period.
 The honest limitations of the $0 baseline: free instances sleep or suspend (Render sleeps
web services, Supabase projects pause after 7 idle days), cold starts on serverless, strict
egress caps (Vercel Hobby 100 GB/mo), and no always-on GPU. Anything requiring a
persistent process, sustained traffic, or model hosting beyond a few GB must either pay
~$5–10/month or burn credits.

## 8 Cost-Free Architecture ($0/month)

Layer                          Free resource                     Verified limits (Aug 2026)
 Git & CI/CD                    GitHub Pro + Actions              3,000 min/mo, unlimited
                                                                  private repos
                                Namecheap .me + Name.com
 Domains & DNS                  domain (1 yr each), Cloudflare    Free; renew via pack next year
                                DNS/CDN
 Frontend                       Vercel Hobby / Netlify            100 GB bandwidth/mo
 API backend                    Cloudflare Workers (100K          Free forever
                                req/day) + Render free (sleeps)
                                Supabase Free (500 MB) + Neon     Free forever; Supabase pauses
 Database                       Free (512 MB) + MongoDB Atlas     after 7 idle days
                                M0
 Auth & billing                 Clerk Pro (student), Stripe (no   While verified
                                fee on first $1K revenue)
 Secrets                        Doppler Team + 1Password (1       Free
                                yr) + GitHub Codespaces secrets
 Error monitoring &             Sentry 50K errors + New Relic     While verified
 observability                  full suite
                                Groq + Cerebras + Gemini free +
 LLM inference                  Mistral + HF Inference +          Perpetual free tiers, rate-limited
                                OpenRouter free models
 GPU notebooks                  Kaggle ~30 h/wk T4 + Colab T4     Weekly limits, ephemeral
                                (12 h sessions)
 Persistent CPU compute         Oracle Cloud Always Free (2       Perpetual, needs card for
                                ARM VMs, 4 OCPU, 24 GB RAM)       signup
 Web scraping                   Zyte Scrapy Cloud 1 unit          Free
                                (forever) + GitHub Actions cron
  Vector data                    Upstash Redis/Qdrant free      Free forever
                                tiers, Astra DB free
                                ElevenLabs free tier (student-
 Speech AI                      expanded), Whisper

[Section continues in full extracted source text.]

## 9 Paid Tier Architectures ($5 / $10 / $25 per month)

$5/month buys one cheap VPS-class anchor: a Hetzner/Contabo-class 2 GB VPS from India
(~$4–5) or an Oracle upgrade, giving a truly always-on backend, reverse proxy
(Caddy/Traefik), and a self-hosted Postgres (1–2 GB) — eliminating Supabase's 500 MB cap
and pause behavior for one project. $10/month adds Replit Core at the student 50% rate
($10 vs $20) with full Replit Agent AI credits and production deploys, or a Supabase Pro
project ($25/mo proration aside) — the biggest unlock is AI coding agent capacity for
accelerated development. $25/month reaches VPS + managed Postgres (Supabase Pro at
$25, or Neon scaling) + a cheap GPU notebook subscription, which is the practical ceiling for
a serious solo developer before Azure credits or startup credits should take over. Each tier
should be justified by a specific project need, not accumulated as subscriptions.

## 10 Student Resource Portfolio (consolidated)

Plain Text
  STUDENT RESOURCE PORTFOLIO — INDIAN STUDENT, AUG 2026

  AI INFERENCE           Groq free · Cerebras free · Gemini free · Mistral free ·
                         HF Inference · OpenRouter free · ElevenLabs free tier
                         (Nominal: ~$50/mo equivalent at dev volume)

  COMPUTE                Oracle Always Free (2× ARM, 24GB) · Kaggle ~30h/wk T4 ·
                         Colab T4 · Azure credits $300 (3–12 mo runway)
  GPU (burst)            Azure T4 ~575h IF quota approved · Kaggle · Modal $30/mo
   DEVELOPMENT               GitHub Pro + Actions 3000min · Codespaces 180h ·
                            JetBrains all IDEs (1yr, renewable) · VS Code
                            GitHub Copilot Free (student plan paused)

  DATA                      Supabase Free 500MB · Neon Free 512MB · Atlas M0 + $50 ·
                            Astra free · Blob LRS via credits

  DEPLOYMENT                Vercel Hobby · Netlify · Cloudflare Workers/Pages ·
                            Render free · Heroku $13/mo × 24mo credit · Container Apps v

  IDENTITY & OPS            Clerk Pro (auth+billing) · Doppler secrets · 1Password 1yr
                            Sentry 50K · New Relic · Stripe first $1K free

  DOMAINS                   Namecheap .me 1yr + SSL · Name.com 1yr


Total nominal value: roughly $5,000–7,000 over 12 months (pack benefits + $300 credits
+ perpetual free tiers at market rate). Real usable value: $2,500–3,500 after exclusions,
expiries, quota friction, and double counting removed (e.g., the GitHub-pack Azure $100 is
the same program the user already used; DigitalOcean is dead; Cloudflare student plan is
US-only).

## 11 Expiration Calendar (sorted by urgency)

Resource        Value            Activate       Expires         Renewal      Urgency
                                                 In a few
 Azure credits   ~$300            Already active months          No           Immediate
 (existing)                                      (check portal
                                                 date)
 Heroku credit ~$312              Only when      24 mo from
 ($13/mo × nominal                needed         redemption      No           Save for later
 24 mo)
 MongoDB $50 $50                  When
 Atlas credits                    upgrading      12 mo           No           Save for later
                                  from M0
 Namecheap /                                                     Renewable    Now —
 Name.com    ~$25 total           Now            12 mo           yearly via   cheap,
 domains                                                         pack         unlocks
                                                                              identity
 JetBrains                        Now (verify                    Annual
 Student         ~$600/yr         via pack)      1 yr            renewal while Now
                                                                 student
  Sentry / New                                  1 yr / while
 Relic / Clerk / tooling        Now            verified        While student Now
 Doppler
 1Password       ~$45/yr        Now            12 mo           Yearly renewal Now
 Google Cloud                   When           1 yr after
 education       ~$50/course    professor      redemption      Per course     Request now
 coupon                         applies
                                When           90 d from       One per
 GCP $300 trial $300            genuinely      activation      account        Save for later
                                needed
 IBM                                                           Renew while
 Academic       trial acct      When needed Semester           enrolled       Save for later
 Initiative
 Modal $30/mo GPU credit        Before a GPU   Monthly         Yes            On demand
                                sprint
 Replit 50%    

[Section continues in full extracted source text.]

## 12 Project Mapping

Argus (research/scraping/orchestration): Zyte Scrapy Cloud unit (forever) for polite
scraping; GitHub Actions cron for scheduling; Supabase/Neon free Postgres for research
data; Azure credits for the egress-heavy collection sprint and the always-on orchestration
worker (B2s, ~$31/mo for 2–3 months); Sentry + New Relic for monitoring; Groq/Gemini free
tiers for classification LLM calls; Azure T4 burst for any embedding-model training.
Workspace OS (SaaS): Clerk Pro (auth + billing — this one benefit covers a large fraction of
the backend), Vercel Hobby frontend, Heroku credit or Container Apps for the API, Stripe
waived fees on first $1,000, MongoDB Atlas credits for operational data, JetBrains for IDE,
1Password/Doppler for secrets.
AI agent projects: free inference tiers round-robin with fallbacks; Kaggle/Colab for
prototyping; Azure T4 hours for any self-hosted model (Llama-class) experiments — only
 after quota approval; Modal $30/mo as a bridge if Azure quota is denied; GitHub
Codespaces 180 h/mo as the dev environment.
General projects: Oracle Always Free ARM VMs (persistent, card needed), free domains,
GitHub Actions CI, Cloudflare CDN/DNS.

## 13 Final Recommendations

Top 10 benefits to pursue: JetBrains Student, Clerk Pro, Sentry + New Relic, MongoDB $50
credits, Heroku 24-month credit, free domains (Namecheap + Name.com), Azure credit
conversion plan, Google Cloud education coupon via your professor, Zyte Scrapy Cloud
unit, Oracle Cloud Always Free.
Activate immediately: domains, JetBrains, Sentry, New Relic, Clerk, Doppler, 1Password,
1Password, Azure quota check, and the Google coupon request to your department. Save
for later: Heroku credit, MongoDB credits, GCP $300 trial, IBM trial, Modal — activate each
when its project is ready. Highest-value AI resources: Groq + Gemini + Cerebras free tiers
(perpetual inference), Kaggle ~30 h/wk GPU, Azure T4 burst (~575 h). Highest-value
compute: Oracle Always Free (perpetual), Azure B2s-class (~3 months), Modal. Best
infrastructure resources: Supabase/Neon/Atlas databases, Vercel + Cloudflare
deployment layer, Clerk auth/billing. Best India-specific: Google Cloud education
coupons, incubator-distributed AWS/Google/Microsoft/DO startup credits, NVIDIA-adjacent
university programs via DLI. Most overlooked: Zyte's perpetual free scraping unit, Stripe's
waived first $1,000, the professor-gated Google coupon mechanism, Heroku's 24-month
credit, and Oracle's 24 GB Always Free ARM pool. Ignore: OpenAI Codex for Students (US-
only), Cloudflare student plan (US-only), v0 for Students (US-only), Alibaba student
program (closed), Thunder Compute (US-only), Cursor/Windsurf discounts (dead), "free
credits list" aggregators.

## 14 Immediate Action List



## 1 Check the exact expiry date of your Azure credits in the portal, and request GPU quota

(NC4as_T4_v3) immediately — approval determines the GPU strategy.

## 2 Claim the JetBrains Student Pack via the GitHub Education link (verify with student ID);

install IDEs today.

## 3 Claim both domains (Namecheap .me + Name.com) and connect both to Cloudflare

DNS — costs nothing, expires in a year, identity anchors for every project.

## 4 Activate Sentry, New Relic, Clerk, Doppler, 1Password through the pack page while your

verification is fresh.
 5. Ask your CS department/faculty to apply for Google Cloud teaching credits at
   edu.google.com and send you the coupon.

## 6 Sign up for Kaggle (free T4 hours) and Oracle Cloud Always Free (card required once).



## 7 Apply to OpenAI Researcher Access and Anthropic External Researcher with a one-page

research note on Argus — real, non-speculative path to $1,000-class credits.

## 8 Register for the Claude Campus next cohort (expected fall 2026) and the Cursor campus

newsletter; watch for fall event credits.

## 9 Set up the Heroku and MongoDB credits as saved assets; redeem only when the

matching project needs them.
10.Begin the Azure conversion sprint: deploy the always-on Argus worker + Postgres on
   credits, schedule the GPU burst if quota is approved, and build the free-tier perimeter
   around it.

## 15 Sources & Verification Dates

All offers verified directly against official provider pages on August 9–10, 2026 unless
noted. [1] GitHub Education — Students & Pack: education.github.com/pack,
github.com/education/students. [2] Azure for Students: azure.microsoft.com/en-
us/pricing/offers/students/. [3] Name.com GitHub students: name.com/partner/github-
students; Namecheap: nc.me/landing/github. [4] Copilot Student pause report:
github.com/orgs/community/discussions/198884 (Apr–Jun 2026). [5] Copilot model-
selection changelog Jun 24, 2026: github.blog/changelog/2026-06-24-changes-to-model-
selection-for-free-and-student-plans/. [6] DigitalOcean exits pack:
github.com/orgs/community/discussions/201240; credit retirement:
digitalocean.com/community/questions/github-student-pack-digitalocean-benefit (Jun
2026). [7] Retired Aug 1, 2026 report: aistudentdiscount.com/digitalocean-github-student-
developer-pack-credits/. [8] Google Cloud for Students: cloud.google.com/edu/students. [9]
GCP education grants docs (updated Jul 29, 2026):
docs.cloud.google.com/billing/docs/how-to/edu-grants. [10] Google Cloud free tier:
cloud.google.com/free. [11] AWS Educate: aws.amazon.com/education/awseducate/. [12]
DigitalOcean Hatch: digitalocean.com/hatch. [13] Oracle Always Free:
oracle.com/cloud/free/. [14] IBM Cloud free + Academic Initiative:
ibm.com/products/cloud/free, ibm.com/academic. [15] Alibaba Cloud students:
alibabacloud.com/en/developer/students. [16] Cloudflare for Students (US-only):
blog.cloudflare.com/workers-for-students/. [17] Replit students: replit.com/edu/students.
[18] v0 for Students: v0.app/students. [19] OpenAI Codex for Students (US/CA):
developers.openai.com/community/students. [20] OpenAI researcher access: openai.com
Researcher Access Program. [21] Anthropic Claude Campus:
 anthropic.com/news/introducing-claude-for-education, claude.com/programs/campus.
[22] Cursor student discount discontinued Jun 25, 2026: cursor.com/help/account-and-
billing/student-discount. [23] Windsurf discount discontinued (Jun 2026), product renamed
to Devin Desktop. [24] ElevenLabs Students: elevenlabs.io/students. [25]
Kaggle/Colab/Modal GPU limits: thundercompute.com/blog/colab-alternatives-for-cheap-
d

[Section continues in full extracted source text.]
