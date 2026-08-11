# Research Notes — 02_LLM_SUPPLY_REPORT_NOTES.md

> These notes are a structured extraction of the supplied report. The original PDF remains authoritative for exact wording, tables and citations.

## 1 Executive Summary

The central question of this investigation — "Can we construct a capable coding-agent
model stack using free and inexpensive models instead of paying for a single premium
model?" — has a clear, evidence-based answer: yes, with real limitations, and the
architecture matters more than any individual model. The findings that led there are
summarized below and expanded throughout this report.
The most important structural fact discovered during verification is that the free API
ecosystem is actively dying and being rebuilt at the same time. In the three months
before this research, GitHub Models was permanently retired (July 30, 2026) 9 ,
OpenRouter delisted more than half of its free models within nine days 8 , Alibaba
discontinued the Qwen Code free tier (April 2026) 10 , and Cerebras silently shrank its free
catalog from roughly a dozen models to two without any deprecation notice, breaking a
real production pipeline with a 404 11 . Any strategy that hard-wires a harness to a single
free endpoint will be broken by a provider decision within months. The correct strategy is
therefore a router-fronted, multi-provider, capability-pinned supply chain, and nearly
every recommendation in this report follows from that fact.
On the model side, the news is genuinely good. Open-weight coding models have reached
the point where a small Mixture-of-Experts model with only 3 billion active parameters
(Qwen3-Coder-Next, 80B total) scores over 70% on SWE-bench Verified with a real
agent scaffold — territory that only frontier commercial models occupied two years ago 3
. In independent small-task agentic evaluations, the free-tier models Gemma 4 26B-a4b
and Qwen 3.5 35B-a3b match Claude Sonnet's score (9/10) 12 . The strongest free-tier
models are no longer toys; they are yesterday's flagships.
The bottleneck is token economics, not raw intelligence. A 50-turn agentic session sends
roughly 25:1 input-to-output token ratio, with input tokens driving 85–90% of the cost,
and a full Claude Code–class session costs roughly ten times more on a frontier model than
on a cheap one ($6.00 vs $0.60 for one session) 13 . Every dollar of budget therefore buys far
more engineering capability wh

[Section continues in full extracted source text.]

## 2 The Current Model Landscape

2.1 Frontier models (the performance ceiling)
Frontier models establish the ceiling that the free/cheap stack should be measured against.
As of mid-2026, the frontier landscape is dominated by Anthropic and OpenAI, with Google
and xAI close behind. On Vellum's aggregated coding benchmarks (March 2026 data),
Claude Sonnet 4.5 leads SWE-bench Verified at 82%, followed by Claude Opus 4.5
(80.9%), Claude Opus 4.6 (80.8%), GPT-5.2 (80%), and Claude Sonnet 4.6 (79.6%) 1 . By
August 2026 the newest generation has moved these numbers further — independent
leaderboards now show Claude Opus 5 at 96–97% and GPT-5.6 at ~96% on SWE-bench
Verified 15 , though the interpretation of those numbers requires caution (Section 5).
 Model family            Representative score    Strength profile        Free access path
 Claude 5 series         Sonnet 4.5: 82% SWE-    Best agentic tool       ~$5 trial only; startup
 (Anthropic)             bench V (Mar) 1 ;       loops, strongest        program up to $25K
                         Opus 5: ~96% (Aug) 15   engineering judgment    16
                         GPT-5.2: 80% (Mar) 1    Strong reasoning,       ~$5 trial; startup
 GPT-5.x series (OpenAI) ; GPT-5.6: ~96% (Aug)   strong Terminal-Bench   credits via VC referral
                          15                     scores                  only 16
                         Gemini 3 Pro: 79.7%     Very large context,     Permanent free tier
 Gemini 3.x (Google)     LiveCodeBench 1         strong all-round        on 3.5 Flash + lite
                                                                         models 2
                         79.4% LiveCodeBench Fast, strong open           $25 signup credit +
 Grok 3.x (xAI)          (3 Beta) 1          coding                      data-sharing program
                         "Best open-weight       Largest open-weight
 Kimi K3 (Moonshot)      coding model" claims    model (2.8T params)     API access only
                         (Jul 2026) 18
 The key strategic point about frontier models is what they do not offer a budget-
constrained user: Anthropic and OpenAI have no permanent free API tier — only one-
time trials of roughly $5 — and their

[Section continues in full extracted source text.]

## 3 The Free API Landscape (Verified August 2026)

3.1 The verified free-tier matrix
Every entry below was verified against official provider documentation during this research
(dates noted). The single most important structural warning, repeated throughout this
report, is that this table expires. Treat it as a snapshot of record and re-verify before
deploying.
 Provider     Free offer   Quotas         Key models Card         Permanenc Commercia
                           (verified)                             e         l use
                           ~15 RPM,                                             Yes, within
 Google       Permanent ~1M     TPM,      gemini-3.5-             Permanent     free quota;
 Gemini 2     free tier on (flash), RPD
                           ~1,500
                                    RPD
                                          flash, 3.5-
                                          flash-lite, No          tier          content
  7           select       resets         3.1-flash-              (document     may train
              models       midnight       lite                    ed)           Google
                           Pacific                                              products
                         30 RPM;   llama-3.3-
              Permanent 14,400 RPD 70b, gpt-                      Stable;
              free tier,           oss-
                         (8B) / 1,000                             catalog
 Groq 21      deepest    RPD       120b/20b, No                   churns        Yes
              catalog    (70B+); 6–qwen3.6-                       slowly
                         12K TPM   27b, llama-
                                   4-scout
                       TPM-based gpt-oss-
                       (~30K TPM 120b, zai-                       Permanent
 Cerebras all hosted snapshot),
            Free tier,             glm-4.7
                       faster TOFT (catalog    No                 tier,     Yes
 22         models     than        volatile —                     catalog
                       OpenAI/Ant was ~12                         unstable
                       hropic      models)
                       ~50K TPM magistral
                       sn

[Section continues in full extracted source text.]

## 4 Free Does Not Mean Useful: Evaluating Free Models

Inside an Agent Loop
Benchmark scores describe potential; an agent harness demands operational reliability.
The evidence on whether free-tier models actually do useful agent work splits into three
quality tiers.
 Tier 1 — Genuinely useful for sustained agent work. Gemini 3.5 Flash (free) is the
standout: it is the same model family as Google's paid flash products, with the same long
context (3.5 models carry very large context windows — 3.5 Flash's context is on the order
of hundreds of thousands to a million tokens depending on version), genuine tool-calling
capability, and the throughput to absorb hundreds of turns per day 2 7 . Groq's free-tier
hosted models (gpt-oss-120b, qwen3.6-27b, llama-3.3-70b) are community-verified as
usable in real coding harnesses — r/LocalLLaMA threads and harness users report Qwen3.6
27B running productive coding-agent sessions 6 26 , and the simonpcouch helperbench
showed Qwen 3.5 35B-a3b and Gemma 4 26B-a4b scoring 9/10 on an agentic refactor
evaluation, matching Claude Sonnet 4.5 on that eval 12 .
Tier 2 — Useful for bounded agent work. Small fast models (GPT-OSS-20b, north-mini-
code, Gemma 4, Phi-class) reliably handle extraction, classification, diff generation, small
patches, test writing, and log analysis. Community consensus across harness forums is that
these models handle "grunt work" lanes well but degrade on 50+ turn planning: they
prematurely start coding, lose task threads in long contexts, and fail to recover from
cascading tool errors 26 27 .
Tier 3 — Tokenically expensive or structurally weak. One token-level weakness affects all
free-lane thinking models that charge output tokens on the same quota as response
tokens: long thinking traces burn the quota. Agentic sessions already run 25:1 input-to-
output ratios; adding thinking tokens multiplies effective consumption 13 . For free tiers
this is a hard engineering constraint — disable or bound thinking depth on quota-sensitive
lanes.
Against the evaluation dimensions in the brief, the composite picture is: code generation is
solid at 70B-free-tier and small-coding-specialist level for single-file and small-module
work, weak at repo-scale architecture; repository u

[Section continues in full extracted source text.]

## 6 Model Router Strategy

6.1 The router is the load-bearing wall of a free-lane stack
The research answer is unambiguous: a router layer is not optional for this use case, it is the
mechanism that converts twelve fragile free tiers into one reliable supply. The ecosystem
offers three classes of solution with distinct tradeoffs.
OpenRouter is the zero-maintenance gateway: a single key exposes 400+ models including
14 free :free endpoints, with an experimental Auto Router that classifies prompts into ~30
task types and routes each to the most-used model for that type, with session stickiness so
a conversation does not mid-switch models 32 . Its weaknesses are exactly the fragility
 documented above (free catalog churn) and the $10 one-time top-up required for full
access 8 .
LiteLLM is the self-hosted control plane and the best fit for this project: open source,
Docker-deployable, and reachable as an Anthropic-compatible proxy at localhost:4000 —
meaning a Claude Code–like harness (or Claude Code itself) can point at the local
router and be provider-agnostic with zero harness changes 33 . The documented recipe
for free-tier Claude Code use is precisely this: map claude-opus-4-8 → NVIDIA NIM's
nemotron-3-ultra (dual-keyed, latency-balanced), claude-sonnet-5 → free OpenCode
models, claude-haiku-4-5 → gpt-oss-120b 33 . Its router implements exactly the switching
logic the brief asks about: latency-based routing, cost-based routing, tag-based pools (free
vs paid), budget enforcement per key, fallback chains with cooldowns and num_retries
(default 3), timeout management, and parameter normalization ( drop_params=true ) so an
Anthropic-only param like thinking is dropped gracefully when a request lands on an
OpenAI-compatible backend 33 . Redis-backed shared state supports multiple replicas.
Coding-agent-native routers (Entelligence Model Router, Cursor Router, commercial
"model swarms") represent the newest tier: Entelligence reports a routing layer solving
71/89 Terminal-Bench tasks for $65.75 where a single frontier model solved 63/89 for
$190.62 — a 79.8% score at 65.5% lower spend 14 . These exist mostly as closed products,
but their per-turn, escalation-aware design is the architecture to

[Section continues in full extracted source text.]

## 7 Multi-Model Agent Architecture

7.1 The role-specialization case
The brief asks whether different models per role (planner, coder, researcher, reviewer,
debugger, cheap worker, summarizer, router) beat one powerful model doing everything.
The 2026 evidence supports specialization — with a budget caveat. Commercial coding
 routers report 30–60% cost reductions at equal or better satisfaction (Cursor Router: ~60%
lower cost, trained on 600K+ live coding requests; Entelligence: Terminal-Bench 71/89 vs
63/89 for a single frontier model) 14 . The mechanism is per-turn escalation: most agent
turns (file reads, small diffs, log parsing, test writing) genuinely are cheap-model work; only
the stuck turns (ambiguous architecture decisions, cascading failures, design forks) benefit
from frontier intelligence, and the router should escalate exactly those 14 32 .
7.2 The single-model case and the tradeoffs
One powerful model doing everything has three real advantages that matter at our budget
level: prompt caching (a stable prefix across turns saves 41–80% of cost when caching is
available — multi-model switching destroys the cache 34 ), behavioral consistency (tool-
call formatting, error recovery style, refusal behavior stay constant — when a fallback uses a
different model, output shape changes exactly when the system is already in an incident 11
), and simplicity. The single-model approach fails on two dimensions: a single free-tier
model alone cannot absorb a full day of agentic work within its quota, and a single paid
model alone destroys the budget (agentic sessions cost 10x per session versus cheap
models 13 ).
7.3 Recommended hybrid role assignment
 Role                             Recommended model class          Rationale
                                  (verified)
 Router / classifier              Local phi-4-mini or GPT-OSS-     Sub-second, free, structured
                                  20b                              output
 Summarizer / context             Local qwen2.5-coder:7b or        Cheap, infinite, offline-capable
 compressor                       gemma-4-26b via Cloudflare
 Cheap worker (extraction, diffs, GPT-OSS-20b, north-mini-code,    Trivial work, don't waste quota
 tests,

[Section continues in full extracted source text.]

## 8 Quota Engineering

8.1 The actual bottlenecks
Three verified facts govern quota engineering. First, tokens per minute (TPM) is the limit
that actually bites: Groq advertises 14,400 requests/day on its 8B model but throttles at
6,000 TPM, which caps the real workload at 2–3 calls/minute on 2,500-token prompts — the
daily cap is never reached because the per-minute cap stops you first 11 . Second, free tiers
vanish mid-request: the Cerebras 404 incident shows that a model a pipeline hard-wired
today may not exist next week 11 . Third, local limit config must match the published tier
— raising your router's configured limits above the real free tier just converts clean local
skips into provider 429s that count against you 11 .
8.2 Designing around limits
The defensive design that follows from these facts has five components. (1) Dual-homing
by capability: every lane is pinned to an open-weight model hosted on at least two
providers (e.g., gpt-oss-120b on Groq and Cerebras and NVIDIA), so a catalog deletion fails
over to the identical weights on another host with no output drift — same-model-different-
provider beats different-model-same-provider 11 . (2) Live catalog enumeration: a
scheduled diff of each provider's model list with alerts catches deletions on day one instead
of through silent failure 11 . (3) Hierarchy of TPM ceilings: when one provider's TPM is
exhausted, spill to the next tier — the measured hierarchy is Gemini ~1M TPM > Mistral ~50K
> Cerebras ~30K > Groq 6–12K > Cloudflare 10K neurons/day > NVIDIA credit-metered 11 23 .
(4) Queue-and-shed, don't queue-and-hang: backing up requests against a rate-limited
provider trades fast failures for slow ones; shed to another provider immediately on 429
with retry-after parsing 11 33 . (5) Budget envelopes per key: LiteLLM budget routing gives
each provider key a spend/quota allowance and auto-fails-over when it is consumed, which
is precisely the A→B→C→D degradation chain the brief diagrams 33 .
8.3 Does context survive a provider switch?
Yes — with one condition. Conversation history, tool state, system prompt, task state, and
reasoning state all live in the harness, not in the model: the harness sends the full message
list 

[Section continues in full extracted source text.]

## 9 Provider Reliability

Measured against uptime, latency, rate-limit frequency, catalog stability, and community
reputation (verified August 2026):
 Provider                      Reliability verdict               Key evidence
                                                                 Permanent documented tier;
 Google Gemini free            Reliable enough for primary       15 RPM/1M TPM is high but
                               lane                              consistent; preview models
                                                                 have stricter limits 7
                                                                 LPU hardware, consistently
 Groq                          Most reliable fast free tier      fast; 30 RPM is low but
                                                                 honored; catalog slowest-
                                                                 churning among fast hosts 11
                                                                 Permanent daily allowance,
 Cloudflare Workers AI         Reliable but compute-limited enterprise       infra; the 10K-
                                                                 neuron ceiling is predictable,
                                                                 not flaky 23
                                                                 Largest stable free catalog
 Mistral                       Stable catalog, moderate limits observed; ~50K TPM; per-
                                                                 model caveats 11
                                                                 1,000+ credits, 40 RPM; trial
 NVIDIA NIM                    Good while credits last           expiration is the failure mode,
                                                                 not uptime 24
                                                                 Gateway itself is stable; free-
 OpenRouter                    Excellent uptime, fragile catalog model   roster churns weekly —
                                                                 treat :free endpoints as
                                                                 ephemeral 8
                

[Section continues in full extracted source text.]

## 10 Local Inference Feasibility (i5-8250U / 8GB RAM)

10.1 What realistically runs
The hardware admits a hard ceiling: an i5-8250U (4 cores / 8 threads, AVX2-class, 2017) with
8GB RAM and integrated graphics cannot run models above roughly 6–7GB of quantized
weights at usable speed. Community-tested CPU figures place Qwen 2.5-Coder-7B at 20–22
tok/s, Llama 3.3-8B at 18–22 tok/s, and Phi-3-mini at 28–32 tok/s at Q4 quantization — but
those figures are from newer CPUs; expect roughly 3–8 tok/s on this laptop, and thermal
throttling on sustained sessions 35 . The MoE revolution helps here in principle (Gemma 4
26B-a4b and Qwen3-Coder-NEXT activate only ~4B/3B parameters), but the total model
footprint of those models (12–45GB) still cannot load into 8GB at usable quantization — the
local option is limited to dense 4–8B or quantized-crippled MoE, which is not practical 12 35
.
 Model (Q4)             Footprint              Speed on this             Role
                                               hardware (est.)
 phi-4-mini 3.8B        ~3GB                   8–15 tok/s                Classifier, router pre-
                                                                         screen
 qwen2.5-coder:7b       ~4.5GB                 4–8 tok/s                 Offline coder fallback,
                                                                         summarizer
 gemma-4-26b-a4b        8–12GB                 1–3 tok/s                 Not practical; exclude
 (Q2–Q3, degraded)
 qwen3-30b-a3b / any    11–20GB                Cannot load               Exclude
 30B+
 10.2 Practical verdict
The honest conclusion the brief demands: local inference on this laptop is a support tier,
not a compute tier. At 3–8 tok/s, an agent turn with a 5K-token prefix takes minutes; a 100-
turn session would take hours of wall time even if the model were competent, and an
agentic loop at that speed is not "useful" by the brief's standard. What local can do well,
with no quota, no network, and no terms-of-service exposure: batch summarization and
context compression (compress yesterday's session at 5 tok/s overnight — the latency is
irrelevant), classification and routing pre-screening, offline fallback for trivial
deterministic tasks, and p

[Section continues in full extracted source text.]

## 11 Cloud + Local Hybrid Strategy

The hybrid the brief diagrams — local model for trivial tasks, free API for normal tasks,
premium fallback for difficult tasks — is practical, but only with the local tier assigned roles
whose latency tolerance is high. The verified-good assignment on this hardware: local =
summarizer/compressor + classifier + offline fallback; free APIs = the entire interactive agent
loop; paid frontier = escalation only. The reverse assignment (local doing the interactive
coding loop) fails on speed, as Section 10 shows. One hybrid role deserves emphasis
because it costs nothing and saves quota everywhere: the local summarizer as the
agent's context-compression service. Every production harness needs compaction;
running it locally against a small coding model instead of a cloud API converts a recurring
token cost into a one-time overnight CPU cost, and the slow speed is immaterial for a batch
job 34 .

## 12 Token Economics

Agentic coding is a fundamentally different cost shape than chat. Vantage's 2026 analysis of
real sessions establishes the numbers 13 : a 50-turn session sends ~1M input tokens
against ~40K output tokens (≈25:1), because every turn re-sends the system prompt,
read files, edits, and the full transcript; input tokens drive 85–90% of the bill; turn-1 inputs
run ~5K tokens while turn-30 inputs run 25–35K, so session cost grows superlinearly
(doubling turns ≈ 3–4x cost); and the same session costs $6.00 on Opus versus $0.60 on a
cheap model. Enterprise Claude Code averages ~$13 per developer active day.
 The reduction levers, ranked by verified impact: (1) model routing — the 10x per-turn
multiplier is the largest lever available and it is free to deploy; (2) context
trimming/compaction — aggressive summarization of completed work stops the input re-
send growth; (3) prompt caching — 41–80% cost reduction when the prefix is stable 34 ,
but agent sessions churn context, so cache hits are lower than in chat apps; (4) tool-output
pruning — keeping only the last ~40K tokens of tool output (OpenCode's pattern) cuts bulk;
(5) short focused sessions — fresh session per task, because retry loops at inflated context
cost disproportionately 13 . One structural note for free tiers: quota is denominated in total
tokens, so these same levers extend free-lane capacity by the same factors — compaction is
quota engineering as much as cost engineering.

## 13 Cost Scenarios

Scenario A — $0/month
Supply: Gemini 3.5 Flash free (~1,500 RPD, 1M TPM) + Groq free (30 RPM, 6–12K TPM) +
Mistral free + Cloudflare 10K neurons/day + local summarizer. Practical capacity: ~5–15M
total tokens/day across lanes on paper; realistically 1–3M tokens/day of useful agent
work because TPM ceilings cap parallelism, not total. Workload: comfortably 2–4 hours of
interactive agent work per day on small-to-medium projects; large-repo work is painful.
Limitations: TPM backpressure during bursts; free catalog churn; no caching discounts;
weak 50+ turn planning on non-Gemini lanes.
Scenario B — $5/month
The marginal dollar buys capacity, not intelligence: it unlocks OpenRouter's full 1,000 RPD
(one-time $10 top-up covers months) and Cerebras Developer 10x limits from $10, and pays
for 5–50M tokens/month of Qwen-flash-class inference ($0.05–0.10/M). Practically: the free
lanes stay as-is, and the $5 buys a paid overflow lane for when free TPM ceilings bind
during a burst — roughly a full extra workday per month at flash-model prices, or a few
hours of a strong open model (qwen3-30b-a3b at $0.05/$0.19) per week.
Scenario C — $10/month
Now the budget can buy one real frontier-quality open model lane: e.g., Qwen 3.7 Max /
GLM-5.2-class API spend (~$0.30–1/M) yields ~10–30M tokens/month of near-frontier
coding. The optimal split at $10: ~$7 on the escalation lane (reserved for stuck turns), ~$2
on overflow, ~$1 buffer. This is where capability jumps most per dollar — going from "free-
tier ceiling" to "near-frontier ceiling" costs under $10/month at 2026 open-model prices,
which was impossible two years ago.
 Scenario D — Occasional credits
Treat credits as ammunition for the escalation lane only: xAI's $25 signup + $150/mo data-
sharing program 17 , NVIDIA's 1,000+ free credits 24 , Alibaba's 1M free tokens per model 20 ,
OpenAI/Anthropic trials (~$5 each) 16 , and any startup/OSS-program credits if the user
qualifies 16 . Strategy: route the escalation lane to the provider whose credits are freshest,
expire-earliest, and largest; never let a credit-bearing provider become the default lane
(terms can change; data-sharing has privacy conditions).
Scenario E — Burst 

[Section continues in full extracted source text.]

## 14 Recommended Model Stacks

Stack A — $0
  Plain Text
  Agent harness (Anthropic/OpenAI-compatible)
          │
          ▼
  LiteLLM proxy (localhost:4000, self-hosted on the laptop)
          │ fallback chain per lane
          ▼
  Gemini 3.5 Flash free (primary; 15 RPM/1M TPM)
   → Groq gpt-oss-120b (dual-home: Cerebras backup)
   → Mistral free devstral/magistral
   → Cloudflare Workers AI (qwen3-30b-a3b, glm-5.2; 10K neurons/day)
   → OpenRouter :free (ephemeral bonus)
   → local qwen2.5-coder:7b (offline fallback/summarizer only)



Stack B — Minimal budget ($5–10/month)
Stack A + OpenRouter with paid overflow (qwen3-30b-a3b at $0.05/$0.19, gpt-oss-120b at
$0.04/$0.17, ling-2.6-flash at $0.01/$0.03 — the cheapest paid models in the ecosystem 8 )
+ Cerebras Developer ($10 one-time) for 10x limits on the same dual-homed models.
Stack C — Maximum capability per dollar (~$10–30/month)
Stack B + a reserved escalation lane at $0.30–2/M (GLM-5.2 via OpenRouter at the 80%-off
promo rate of $0.2772/$0.8712, or Qwen 3.7 Max direct 8 20 ) + periodic frontier bursts
(Anthropic trial/startup credits when available; Anthology/VC credits if eligible). The $10–30
 band now reaches ~90% of frontier agentic capability on most turns because the strong
open models genuinely closed the gap 1 3 .
Stack D — Local-first
Not viable as primary on this hardware; viable as written in Section 10 with the local tier
promoted only for overnight/batch/offline work. Revisit if hardware ever reaches ~24GB
RAM or a modest GPU — at that point a Qwen3-Coder-30B-class MoE local loop becomes
the most cost-efficient architecture that exists 5 26 .

## 15 Project-Specific Recommendations

Argus (research synthesis, long-context reasoning, evidence evaluation, multi-agent
orchestration): lean on Gemini 3.5 Flash free — its long context and included grounded
search (5,000 requests/month) map directly to research synthesis, and its free quota is the
largest of any high-quality model. Escalate evidence evaluation to the paid lane; the 25:1
input ratio of research sessions makes cheap routing doubly important 2 13 .
Workspace OS (full-stack coding, UI, APIs, DevOps): the coding-specialized lane —
qwen3.6-27b / GLM-5.2 / Qwen3-Coder-30B-class across Groq, Cloudflare, and
OpenRouter — is the correct engine; these models beat general models at this size on code
tasks 1 3 . UI work needs a model with genuine structured-output reliability (Gemma 4
and north-mini-code are solid free options); DevOps/debugging loops favor Groq's speed.
Agent/automation projects (tool calling, MCP, scripting, multi-step): tool-calling
reliability is the selector — prefer gpt-oss-120b (dual-homed, strong BFCL-class calling)
and Mistral's devstral/magistral; keep per-turn escalation for MCP chains that stall 14 33 .
General development (coding, Git, Docker, deployment, docs): Stack A/B as the daily
driver; documentation and small fixes are cheap-lane work, architecture decisions are
escalation-lane work.

## 16 Failure Analysis

Every recommended component, with its known weaknesses, per the brief's demand to
design around weaknesses rather than hope.
 Component               Bad at                 When NOT to use           Failure mode
 Gemini 3.5 Flash (free) Deep multi-file        Sensitive IP you don't    Quota throttle at
                         architectural          want used for training;   sustained bursts; per-
                         reasoning; free tier   tasks needing refusal-    model free allocation
                         output trains Google                             can be quota-zero'd
                         products; preview          resistant instruction    without warning
                        siblings have tighter      following                (observed on 3.1-pro-
                        limits 7                                            adjacent models) 11
                        30 RPM is low for
                        parallel work; long-
                        context tasks burn the     Parallel multi-agent     429 bursts; TPM hard
Groq free               TPM ceiling;               work; 100K+ context      stop 21
                        occasional model           tasks
                        delistings (Kimi K2
                        was dropped)
                        Catalog stability; only    Anything hardcoded       Silent 404 when
                        2 models currently;        to a model name;         models vanish; output
Cerebras free           small-model                production pipelines     shape changes at
                        performance gaps           without catalog          failover 11
                                                   monitoring
                        Per-model caveats          Assuming "free"
Mistral free            vary; experimental-        applies uniformly        Model-specific 403s 11
                        program quotas             across the catalog
                        reported shrinking
                        Three-week catalog         Recurring missions       Delisting; broken
OpenRouter :free        half-life; random          pinned to one :free      assumptions about
                

[Section continues in full extracted source text.]

## 17 The Strategic Question

Is it smarter to spend our effort obtaining the best possible model, or building a better
  agent harness around merely good models?
The 2026 evidence answers decisively: for budgets of $0–30/month, the harness is the
higher-leverage investment — up to the point where the model is too weak to sustain
the tool loop at all. Three findings support this. First, harness effects dwarf model effects
at the margins that matter to us: the same model scores between 28% and 70% on the
same benchmark under different scaffolds 4 31 , and routing/orchestration layers report
solving more tasks for 65% less spend than a single frontier model 14 . A better harness
(compaction discipline, tool design, escalation rules) buys 10–40 point gains; a model swap
within a tier buys 5–10. Second, the free/open ecosystem already contains models (Gemini
3.5 Flash, gpt-oss-120b, Qwen3.6/GLM-5.2-class) that clear the "sustains a 50-turn tool
loop" bar 2 12 20 — so the "merely good" in this question is genuinely good enough for
the majority of turns. Third, the one place the model is not compensable is long-horizon
planning and stuck-turn recovery: when a model cannot hold a task thread across 30+
turns or recover from a cascading tool failure, no harness fully compensates — the failure is
at the reasoning core, and the fix is escalation spend or hardware, not orchestration.
The decision rule that follows: spend engineering effort on context management, tool
reliability, and routing/escalation policy first (they compound across every model and
every budget), spend money on the escalation lane second (the one place the model is not
compensable), and never spend significant effort or money chasing marginal model
improvements within a tier.

## 18 Long-Term Architecture: The Model Abstraction Layer

The target architecture is exactly the diagram in the brief's Section 21: the agent system
speaks only to a Model Interface (a LiteLLM proxy at localhost:4000 implementing the
Anthropic Messages API or OpenAI Chat Completions API), below which sit the Model
Router (LiteLLM's router with fallback chains, budgets, and cooldowns) and the Local
Runtime (Ollama at localhost:11434 , OpenAI-compatible), both feeding provider pools. This
layering decouples the agent from every provider simultaneously: Anthropic's terms,
Google's catalog changes, Groq's delistings, and local hardware upgrades all become
configuration edits to the router's YAML, not agent rewrites 33 . Existing standards reinforce
this: the OpenAI-compatible chat format is the de facto lingua franca (adopted by Groq,
Cerebras, NVIDIA, Cloudflare, HF Router, DashScope, OpenRouter); MCP (Model Context
Protocol) is becoming the standard tool/connector layer independent of model; and the
production harnesses themselves already expose this abstraction (Claude Code's
 ANTHROPIC_BASE_URL , Codex's OPENAI_BASE_URL , the claude-code-router plugin ecosystem
for arbitrary models) 33 . The agent should additionally own its session state externally
(task log, file-read cache, compaction summaries in local files) so that a model switch —
even a provider death mid-task — leaves all recoverable state intact.

## 19 Immediate Experiment (≈$0, executable today)

Design, per the brief's Section 23. The experiment compares four lanes on one fixed task in
one fixed repository:
Task: clone a medium Python repository (~5–20K lines, e.g., a utility CLI or small web
service with an existing test suite), then instruct the agent to implement one clearly-scoped
feature (add a CLI flag with validation, or add an endpoint with tests) and fix one injected
bug.
Lanes (all free): (1) Gemini 3.5 Flash free; (2) Groq gpt-oss-120b ; (3) OpenRouter
 cohere/north-mini-code:free + poolside/laguna-s-2.1:free (small coding specialists); (4) local
 qwen2.5-coder:7b via Ollama. Same harness prompt, same tools (file read/write, git ,
 pytest ), max 60 turns per lane.
Measure: completion (feature working + tests passing), tool calls, user interventions, tests
passed/failed, bugs introduced, wall time, total tokens (input/output/thinking), effective
cost, context failures, and recovery count (failed command → diagnosis → fix cycles). Run
each lane twice and average; record the free-tier rate-limit events encountered per lane as a
reliability datapoint.
Decision rule: the winning lane becomes the default coder; the lane with the best recovery
count per token becomes the escalation candidate when the default stalls; the local lane's
measured tok/s decides whether it earns the summarizer role. This delivers the report's
own insistence that harness performance, not leaderboard rank, selects the model.
 20. Sources and Verification Dates
All sources verified August 8–9, 2026 unless noted. Full URLs:
[1] Vellum — "Best LLM for Coding" (verified Mar 2026 data):
[2] Google AI — Gemini API Pricing (verified 2026-08-05 ):
[3] QwenLM — Qwen3-Coder blog:
[4] Alibaba Cloud — Qwen3-Coder-Next:
[5] Atomic Chat — Best Local LLMs for Coding 2026 (2026-08-07 ):
[6] Faros AI — Best open-weight models for coding (2026-07-09 ):
[7] Google AI — Gemini API Rate Limits (verified 2026-08-08 ):
[8] Teamday — Best free AI models on OpenRouter (2026-08-05 ):
[9] GitHub — GitHub Models retirement notice (verified 2026-08-08 ):
[10] Alibaba Cloud — Model Studio GLM docs (verified 2026-08-02 ):
[11] ianlpaterson.com — Free LLM API audit (2026-05-31 snapshot + follow-ups ):
[12]

[Section continues in full extracted source text.]
