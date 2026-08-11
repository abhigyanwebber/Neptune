# Research Notes — 01_HARNESS_REPORT_NOTES.md

> These notes are a structured extraction of the supplied report. The original PDF remains authoritative for exact wording, tables and citations.

## 1 Executive Summary

Claude Code is the most polished agentic coding harness available in 2026, but it is
proprietary, closed-source, and has no free tier. Anthropic bundles it into its Max plans
($100/month) and Super Max plans ($200/month), and heavy users report costs of $150–200
per month on the API 20 . For a developer with a limited budget, this creates a genuine
decision problem: is the Claude Code harness itself worth paying for, or can the same
experience be reconstructed with an open-source harness plus a cheaper model?
This report answers that question based on verified facts rather than marketing. The
investigation covered thirteen serious alternatives — Aider, Codex CLI, Gemini CLI
(transitioning to Antigravity), Crush (the project formerly known as OpenCode), Cline,
Roo Code, Kilo Code, OpenHands, Goose, Continue, Qwen Code, and Amazon Q
Developer — plus Claude Code's own documented architecture from official Anthropic
documentation.
The headline findings are:
 1. The harness and the model are separable, but not equally important. Independent
    evidence from 2026 shows that with the same frontier model (Opus 4.5), the best third-
    party harnesses solve almost as many problems as Claude Code — a 2–3 percentage
    point spread 20 . But the spread between models in the same harness is much larger
    (88.0% vs. 74.2% on Aider's polyglot benchmark) 11 . On hard problems the model
    dominates; in daily workflow the harness dominates.
 2. A real zero-cost Claude Code experience exists. Google's Gemini CLI (Apache-2.0)
    offers a genuinely free tier of 1,000 requests per day with 1M-token context, running a
    fully agentic loop — file editing, terminal execution, MCP, skills, checkpoints, headless
    mode 16 . Amazon Q Developer's free tier adds 50 agentic requests per month on
    current Claude models via AWS Builder ID, with no AWS account required 31 32 .
 3. The open-source harnesses are converging on Claude Code's architecture. Aider's
    repo-map and edit-format design, Codex CLI's OS-level sandbox, Gemini CLI's extension
     system, and Cline/Roo's mode-based permission groups replicate most of what makes
    Claude Code valuable. Differentiation has mo

[Section continues in full extracted source text.]

## 2 Claude Code Technical Baseline

Anthropic describes Claude Code as "the agentic harness around Claude: it provides the
tools, context management, and execution environment that turn a language model into a
capable coding agent" 1 . It is essential to be precise about what is documented, what is
observed, and what is speculation, because much popular writing about Claude Code's
internals still traces back to a February 2025 leaked source repository whose architecture
has since diverged from the shipping product. Anthropic has continued to ship hooks, skills,
subagents, MCP tool search, dynamic workflows, and sandboxed execution after the leak,
and the leaked code should be treated only as historical background, never as current
documentation 8 .
2.1 Agent loop
The documented loop is a classic agentic cycle: gather context → take action → verify
results, repeated in a while-loop where the model reasons, chooses a tool, executes it,
observes the result, and decides the next step 1 . The loop is single-threaded in its main
session; parallelism is achieved through subagents rather than threads. The Agent SDK
exposes the same loop programmatically in Python and TypeScript, confirming the
 architecture without exposing source code 7 . Permission enforcement happens outside
the model — the harness, not the model, decides what is allowed — which is Anthropic's
explicit design position: "bypassing permissions is zero-maintenance but offers no
protection" 34 .
2.2 Tool system
The core tool set is hard-coded into the harness: Read, Write, Edit, Bash, PowerShell,
Grep, Glob, Ripgrep, WebFetch, WebSearch, LSP (live code intelligence), Agent (subagent
spawning), and AskUserQuestion 2 . Bash commands run in separate processes with a 2-
minute default timeout (ceiling 10 minutes), 5GB output kill switch, and 30,000-character
default read-back 2 . Read-only tools such as Read, Grep, and Glob do not prompt inside
the working directory 2 . MCP tools are layered on top of this fixed core; they appear as
regular tools with the same permission and hook handling, and Claude Code uses tool
search to keep only tool names in context until a tool is first used, deferring full definitions
— a deliberate context-cost optim

[Section continues in full extracted source text.]

## 3 Agent-Harness Architecture: What Is Actually

Underneath
Every serious coding agent in 2026 is built from the same five subsystems. The differences
between tools are differences in how well each subsystem is implemented and what each
subsystem is allowed to do by default — not differences in kind. Understanding the shared
skeleton makes the per-tool analyses in Section 5 much faster to absorb.
3.1 The agent loop
The universal pattern is reason → act → observe → decide-again: the model receives a
prompt plus gathered context, emits a tool call (or a plan step), the harness executes it in
the real environment, feeds the output back, and the cycle repeats until the goal is met, the
user intervenes, or a limit is hit. Explicit planning varies: aider has architect mode and / -
command-driven chat modes; Codex CLI uses a plan-then-execute flow exposed through
 /permissions and checkpoints; Roo Code and Cline expose Plan/Act toggles; Goose runs a
Plan→Act→Observe cycle with an implicit planning phase inside the model's own
reasoning 9 13 22 27 . Error recovery is nearly universal — a failed shell command or linter
error becomes part of the observation and the model retries — but the quality of retry
strategies is where harnesses diverge; Aider deliberately retries with AST-level syntax
checking, and Claude Code's thrashing guard is the most sophisticated published example
 2 8 10 .
3.2 The tool layer
Tools fall into three implementation classes, and this classification explains much of the
extensibility difference between tools:
 Tool class                     Definition                       Examples
                                 Tools compiled into the         Claude Code's Read/Edit/Bash
 Hard-coded core                harness binary; consistent      set 2 , Codex CLI's sandboxed
                                behavior, vendor control        toolset 14
                                Any Model Context Protocol      All surveyed tools; the de facto
 MCP-based extension            server adds tools dynamically   universal extension mechanism
                                at runtime                       4 16
                                Structured bundles (SKILL.md    Claude Code skills 6 , Codex
 Plugin

[Section continues in full extracted source text.]

## 4 The Landscape of Alternatives

The market has organized into four tiers. Recognizing the tier a tool belongs to prevents
false comparisons:
 Tier                           Character                      Members found
 Terminal agents (Claude        Real codebases, file + shell   Gemini CLI, Codex CLI, Crush
 Code–like)                     access, agentic loop           (ex-OpenCode), Aider, Qwen
                                                               Code, Amazon Q CLI
                              Same loop inside VS              Cline, Roo Code, Kilo Code,
 IDE agents                   Code/JetBrains, often with CLI   Continue
                              mode
                              Sandboxed VMs, long-running
 Full autonomy platforms      tasks, SDK to build agent        OpenHands
                              systems
 General-purpose agent shells Code  plus research/workflow
                              automation, MCP-centric          Goose

Vendor-locked IDEs (Cursor, Windsurf) and proprietary CLI agents (Grok Build) were
reviewed for completeness but excluded from deep analysis because they fail the free-or-
cheap criterion of the brief 41 . Two provenance notes matter for credibility: OpenCode was
renamed Crush and now lives at charmbracelet/crush (the original opencode-ai/opencode
repository is archived) 18 19 , and Kilo CLI explicitly descends from OpenCode ("a fork of
OpenCode, enhanced") — the OpenCode lineage has splintered into Crush (original author,
Charm) and Kilo Code 18 23 . Gemini CLI is being succeeded by Google's Antigravity
product line; the open-source CLI remains fully maintained (latest commits the day before
this report) and the transition is described as additive for open-source users 16 20 .
 A note on research quality: an initial round of LLM-assisted deep dives produced stale and
hallucinated facts (wrong star counts, wrong dates, an invented claim that "Aider is the
modern successor to Codex CLI"). Those were discarded and replaced with facts verified
directly against the GitHub API, official documentation, and 2026-dated independent
analyses. Repository metadata below was fetched from the GitHub API on August 8, 2026 41
 20 .
 Tool           Re

[Section continues in full extracted source text.]

## 5 Individual Tool Analyses

Each tool below is analyzed on architecture, context, extensibility, autonomy, model
support, cost, security, and forkability. Facts are verified against official documentation and
the GitHub API; claims from secondary sources are marked.
5.1 Aider — the veteran model-agnostic harness
Identity. Aider is the longest-lived open-source agentic pair-programmer (since 2023, Paul
Gauthier), Apache-2.0, 48K stars, with the largest deployed open-source user base in this
category — reportedly 4.1 million installs and 15 billion tokens per week through mid-2025
 9 41 . The entire agent loop is readable Python with no proprietary components.
Architecture. Aider's design philosophy differs from Claude Code's: it is git-native rather
than session-native. It auto-commits after edits, can undo its last commit, and treats the
repository — not a session file — as the unit of memory. The loop is
read→plan→edit→verify, with AST-level syntax checking and automatic error feedback to
the model 9 10 . Architect mode ( /architect ) splits reasoning from editing: a strong model
plans, a cheap model writes, cutting cost dramatically (78.2% on the polyglot benchmark
with o3 + gpt-4.1 architect mode versus 88.0% for gpt-5 high, at a fraction of the cost) 11 .
Chat modes ( /code , /architect , /ask ) make the modes explicit; /test runs a shell command
and injects failure output into context.
Context. The repo map — aider's signature innovation — is a tree of files and symbol
signatures compressed with ctags, giving the model a global view without loading files 9 .
 /tokens reports usage, /drop frees context, /add adds files, /read-only references without
expanding.
Model support. Fully model-agnostic through LiteLLM: any OpenAI-compatible API,
OpenRouter (200+ models), Ollama and LM Studio for local models, and a documented free
path — OpenRouter free-tier models and the Gemini free API 10 . Aider is candid about
limits: models below roughly GPT-3.5 class fail to produce the required edit formats, and
the polyglot leaderboard shows edit-format compliance as a hard gate 10 11 .
Cost and Windows. A single pip install works on Windows (including PowerShell/WSL). The
harness is free; moderate u

[Section continues in full extracted source text.]

## 6 Detailed Comparison Matrix

The matrix below uses verified facts; it deliberately avoids numeric scores for properties
that cannot be scored honestly (e.g., "reliability" depends on the model plugged in).
Symbols: Y = yes, P = partial, N = no, — = not applicable / not documented. Full reasoning
for the contentious cells follows the table.
6.1 License, platform, and installation
 Capabili Claude       Aider       Codex      Gemini     Crush       Cline      Roo        Kilo
 ty       Code                     CLI        CLI                               Code       Code
 Open       N
 source     (propriet Y            Y          Y          Y           Y          Y          Y
            ary)
            None / Apache- Apache- Apache-               MIT-        Apache- Apache- MIT
 License    proprieta 2.0     2.0      2.0               family      2.0     2.0
            ry
                              Y        Y                 Y                                 Y
 Local      Y                 (PowerS
                      Y (pip) hell/npm (npm/br           (winget/ Y (VSIX)      Y (VSIX)   (npm
 install                               ew)               scoop)                            rl)
                              )
 Windows Y             Y           Y          Y          Y           Y          Y          Y
 support
 Terminal Y                                                          P (IDE-    P (IDE-    P
 -first                Y           Y          Y          Y           first +    first)     (platf
                                                                     CLI)                  m)
 IDE                                          Y (VS      Y (ext
 integrati Y (ext)     N           Y (ext)    Code)      beta)       Y          Y          Y
 on
 6.2 Tools and agent capabilities
 Capabili   Claude   Aider     Codex      Gemini    Crush      Cline       Roo       Kilo
 ty         Code               CLI        CLI                              Code      Code
 File       Y        Y         Y          Y         Y          Y           Y         Y
 editing
 Terminal                      Y
 executio   Y        Y         (sandbox Y           Y          Y           Y         Y
 n            

[Section continues in full extracted source text.]

## 7 Architecture Comparison in Depth

This section answers the brief's architecture investigation questions directly, tool by
capability family.
7.1 Agent-loop designs and error recovery
Three loop families emerged. The plan-execute-verify family (Codex CLI's plan-then-act
with checkpoints, Amazon Q's q dev , Kilo's plan mode) front-loads planning and is best for
bounded tasks 13 31 23 . The iterative pair-programmer family (Aider, Crush, Gemini CLI)
reason-and-act in a tight loop with aggressive verification hooks — Aider's AST syntax check
and /test injection are the strongest published error-recovery mechanisms 9 18 16 . The
event-stream/platform family (OpenHands, Cline's SDK loop) structures every interaction
as an observable event, which trades loop speed for transparency and programmability 24
21 .
 Recovery quality correlates with harness maturity, not marketing: Claude Code's thrashing
guard (error out instead of looping on oversized output) and Codex CLI's git checkpoints
before/after tasks are the two most robust published mechanisms; Aider's /undo (revert
last commit) is the simplest equivalent 8 13 9 .
7.2 Context architectures compared
 Tool              Repo overview     Compaction        Persistence    Distinctive
                                                                      mechanism
                                   Auto   (outputs                    MCP tool-search
 Claude Code       LSP symbols +   first, then       JSONL sessions + deferral;
                   file load       summary)          checkpoints      thrashing guard
                                                                       2 8
                   Repo map        Manual (/drop, Git history +       Git is the
 Aider             (ctags)         map refresh)      history files    memory system
                   AGENTS.md +     Sliding +                          OS-scoped
 Codex CLI         loaded files    summarization      codex resume    writable roots 13
                                                                      1M-token
 Gemini CLI        GEMINI.md +     Summary     skill Checkpoints      context reduces
                   loading                           (save/resume)    need to compa

[Section continues in full extracted source text.]

## 8 The Most Important Question: How Useful Are These

Without Claude?
8.1 The evidence
The brief's central question — if we put an excellent harness on a different model, how
much of the Claude Code experience survives? — now has empirical answers that did not
exist a year ago.
Evidence 1: the scaffolding effect is real but small. With the same model (Opus 4.5),
Augment's Auggie solved 17 more problems than Claude Code out of 731 SWE-bench
instances — a meaningful but modest difference, and the verdict of independent analysts is
explicit:
   "Same model, different scaffolding. The agent's architecture matters as much as the
  model underneath." 20
But note the direction: the best harness beats Claude Code's harness by ~2.3%, meaning
harness quality is a second-order effect at the frontier.




Evidence 2: the model effect is large. Aider's polyglot leaderboard, same harness
throughout: gpt-5 high 88.0%, gpt-5 medium 86.7%, gemini-2.5-pro 83.1%, gpt-5 low 81.3%,
o3+gpt-4.1 architect 78.2%, DeepSeek-V3.2 74.2% — a 14-point spread within one
harness, versus ~5 points between harnesses on SWE-bench 11 20 . vals.ai's minimal-
harness experiments (a bash-only scaffold with ~100 lines of Python reached 65% on SWE-
bench Verified) confirm the same asymmetry: the harness sets the floor, the model sets the
ceiling 38 39 .
Evidence 3: edit-format compliance is a hard gate. Aider's documentation warns that
models below roughly GPT-3.5 class fail to produce valid edit blocks, and leaderboard data
shows "well-formed edit %" as the deciding factor for weak-model performance 10 11 .
Community reports on Roo/Cline echo this: 7B local models frequently break the XML tool-
calling contract 22 . The harness cannot rescue a model that cannot follow its protocol.
Evidence 4: the model layer is now the competitive frontier. August 2026 SWE-bench
leaderboard scores (95–97% range, multiple vendors, saturation concerns noted) show the
frontier models converging; independent commentary stresses that benchmark saturation
makes real-world reliability the actual differentiator, which remains correlated with model
choice 40 42 .
8.2 Answer by tool
 Tool                   Coupling              Optimization           Open-model
                   

[Section continues in full extracted source text.]

## 9 Cost Analysis

9.1 The real cost landscape
Claude Code's pricing structure forces a binary decision: $20/month (Pro, limited) or $100–
200/month (Max/Super Max), with heavy usage reaching $150–200/month even on Max
according to independent developer reporting — and no free tier at all 1 20 . Against that,
the open ecosystem offers four budget tiers:
 Tier                   Setup                  Monthly cost           What you get
                        Gemini CLI (Google                            Full agentic harness,
 $0                     sign-in)               $0                     1,000 req/day, 1M
                                                                      context 16
 $0                     Amazon Q free tier     $0                     50 frontier-Claude
                        (Builder ID)                                  requests/month 32
                        Aider/Cline/Roo +                             Full harness;
                        free or cheap models                          DeepSeek scored
 $0–5                   (OpenRouter free tier, ~$0–5                  74.2% on Aider's
                        Gemini free API,                              polyglot benchmark at
                        DeepSeek ~$0.27–1/M                           $1.30/batch 10 11
                        tokens)
                         Codex CLI via ChatGPT                          Fast frontier harness,
 $20                    Plus (if already      $0 marginal              OS sandbox, review
                        subscribed)                                    strength 13 14 20
                        Claude Code                                    Frontier harness +
 $100–200               Max/Super Max           $100–200+              frontier model +
                                                                       support




Aider's own leaderboard is the best published capability-per-dollar evidence in the survey:
gpt-5 at low reasoning effort scored 81.3% at $10.37 per batch versus 88.0% at $29.08 at
high effort — the last 7 points cost nearly 3× — while DeepSeek-V3.2 delivered 74.2% at
$1.30, a 95% cost saving for a modest score drop 11 . Architect mode 

[Section continues in full extracted source text.]

## 11 Relevance to Your Projects

11.1 Argus (deep-research orchestration: research agents, evidence
acquisition, web research, orchestration, knowledge bases)
Argus is less a coding task and more an agent-systems infrastructure task. The tools that
map to it are those with real subagent/multi-agent architecture and web-research
 capability: OpenHands is the closest published substrate — a multi-agent platform with
SDK, event streams, sandboxed runtimes, and an evaluation harness you could adapt 24 25
; Goose is purpose-built for research-plus-implementation workflows (RPI pattern, Ralph
Loop, Playwright, observability) and lets you compose agents from MCP extensions 27 ;
Claude Code's agent teams remain the best-published single-harness multi-agent design
but are proprietary 2 ; Cline's Kanban (parallel agents with worktrees and dependency
chains) and Qwen Code's daemon + IM bots offer useful architectural ideas 21 30 .
Recommendation: use OpenHands or Goose as the Argus substrate, Aider for the
surrounding Python infrastructure — and study Claude Code's agent-teams
documentation as a design reference without paying for it.
11.2 Workspace OS (application-like workspaces/environments)
This is rapid full-stack build-and-maintain work with many small systems. The best fit is
harnesses with strong git discipline and low-friction headless operation: Aider (git-native,
cheapest per-rupee for iterative building), Codex CLI (fast generation, built-in review mode,
cloud sandboxes for trying things) 13 , and Gemini CLI ($0 daily driving) 16 . IDE agents
(Cline/Roo/Kilo) add value if Workspace OS development happens inside VS Code,
particularly Kilo's Memory Bank for cross-session project memory 23 . Qwen Code's
daemon mode is architecturally interesting if Workspace OS workspaces should each run
their own agent service 30 .
11.3 AI-agent / automation projects (agent development, API
integration, browser automation, MCP development, multi-agent
systems)
This lane is Goose's home turf: MCP development is its core mechanism, extensions are
literally MCP servers, and its general-purpose orientation covers browser automation
(Playwright skill), API integration, and task automation 27 . Continue deserves a slo

[Section continues in full extracted source text.]

## 12 Open-Source and Forking Potential

12.1 Genuinely open source versus open-source interface
The brief's distinction matters. The classification, verified against repository licenses and
documentation:
 Category                          Tools                           Meaning
                                   Aider (Apache-2.0, Python),
                                   OpenHands (MIT, Python),
 Open-source agent                 Goose (Apache-2.0, Rust),       Can be forked and re-
 infrastructure (loop, tools,      Cline/Roo/Kilo (TypeScript),    architected 9 24 26 21 28
 prompts all readable and          Continue (Apache-2.0), Gemini   16 18 30
 modifiable)                       CLI (Apache-2.0, TypeScript),
                                   Crush (MIT-family, Go), Qwen
                                   Code (Apache-2.0)
                                 Amazon Q CLI (MIT wrapper,
                                proprietary Bedrock agent),
 Open-source interface /        Codex CLI partially (Apache-2.0 Forkable shell, not forkable
 closed brain                   CLI, but tuned for proprietary intelligence 31 13
                                OpenAI models)
                                Claude Code CLI (Agent SDK
 Proprietary                    under commercial terms, not Cannot be forked at all 7 41
                                repackagable), Cursor,
                                Windsurf, Grok Build


12.2 Forkability assessment of the genuine candidates
Forkability is not only about the license — it is about codebase complexity, language,
modularity, and maintenance burden. Assessed in descending order of suitability as a
foundation:
 1. Aider — the best foundation overall. Python, clean separation (coders/edit formats,
    repo map, chat modes, LiteLLM provider layer), the harness is the orchestrator-over-
    models design you would build anyway, and its edit-format layer is a proven innovation
    you could reuse directly. Apache-2.0 permits commercial modification 9 10 .
 2. OpenHands — the best foundation if the destination is a multi-agent platform rather
    than a coding assistant: full SDK, event-stream architecture, runtime abstraction,
    evaluation harness included. Hea

[Section continues in full extracted source text.]

## 14 Final Recommendations

14.1 Best overall replacement
Codex CLI — if ChatGPT Plus ($20/month) is already part of your stack, it is the strongest
Claude Code replacement: 80% on SWE-bench Verified within reach, the fastest terminal
harness in independent tests, built-in OS-level sandboxing (the best default security
posture of any CLI surveyed), review-first strengths, subagents, and a genuine free-adjacent
cost if you would pay for ChatGPT anyway 13 14 20 . If the $20 subscription itself is the
problem, the answer below shifts to the free tier.
14.2 Best under severe budget constraints (free)
Gemini CLI with Google sign-in. One thousand agentic requests per day, 1M-token
context, full file/shell/MCP/checkpoint/headless capability, Apache-2.0, at $0 16 . Layer on
Amazon Q's free tier (50 frontier-Claude requests per month) for the rare hard problem
where Gemini's model falls short 32 . This combination — $0/month — reproduces roughly
85–90% of the Claude Code daily experience, which is the factual answer to the budget
question: you do not need to pay to enter this market.
14.3 Best open-source foundation for modification
Aider. Python, Apache-2.0, the entire loop readable, the cleanest orchestrator-over-models
architecture in the survey, a proven and reusable edit-format layer, and — uniquely — a
published leaderboard that lets every model decision be made on evidence rather than
faith 9 11 . OpenHands is the correct answer if the destination is a multi-agent platform
rather than a coding harness 24 .
14.4 Best for your projects
  • Argus → OpenHands (or Goose for research-heavy workflows). Only these two provide
   true multi-agent substrate rather than assistant ergonomics 24 27 .
 • Workspace OS → Aider (git-native building discipline) plus Gemini CLI ($0 daily driver)
    9 16 .
 • Agent/automation → Goose (MCP-native general agent shell) plus Continue's
   workflow dashboard for cron/webhook automation 27 28 .
 • General software → Codex CLI (speed/review) with Aider as the cheapest serious-
   work backup 20 11 .
14.5 Best experimental choice to install first
Gemini CLI — five minutes on npm, zero keys, zero cost, and the resulting hands-on
experience (agentic loop, checkpoints, M

[Section continues in full extracted source text.]

## 15 Installation and Experiment Plan

Three tools, chosen to triangulate the decision: Gemini CLI ($0 harness+model), Aider ($0–
5 harness + choose-your-model control), Codex CLI (free-if-ChatGPT-plus speed and
sandbox). This set spans the three decisive variables — cost, model-agnosticism, and
default security posture — with no two tools overlapping on all three.
15.1 Tool 1: Gemini CLI
  Item                   Detail
                         npm i -g @anthropic-ai/claude-code → No —
                        correct command: npm i -g @google/gemini-cli
 Installation           (Windows: also winget install Google.GeminiCLI );
                        then gemini auth login with a Google account
                        None required for free tier (Gemini 3 models
 Model config           via Google sign-in); API-key path:
                         GEMINI_API_KEY from AI Studio for billing
                        upgrade 16
 API keys / free        None. $0. 60 req/min, 1,000 req/day 16
 Recommended model      Default Gemini 3 (free); upgrade only if the
                        experiment shows the free model ceiling is hit
 First test task        The standardized task in 15.4
 Expected limitations   Rate limits; non-Claude reasoning ceiling;
                        telemetry on by default 16
 Metrics to observe     Interventions per task, cost ($0 baseline), test
                        pass rate, planning fidelity


15.2 Tool 2: Aider
 Item                   Detail
                         pip install aider-chat (Windows
 Installation           PowerShell/WSL); git must be installed since
                        Aider is git-native 9
                        aider --model PROVIDER/MODEL — e.g.,
 Model config           openrouter/deepseek/deepseek-v3.2 or
                        gemini/gemini-2.5-pro (free API); .env with
                        OPENROUTER_API_KEY etc. 10
                        Free path: OpenRouter free-tier models or
                        Gemini free API; paid path: any provider key;
 API keys / free        typical moderate use $10–15/month,
                        DeepSeek orders of magnitude cheaper 10
                           deepseek/deepseek-v3.2 (best documented
 Recommended m

[Section continues in full extracted source text.]

## 16 The Decisive Answer

If we cannot afford Claude Code, what should we actually use instead, why, and
  what would we be giving up?
Use instead: Gemini CLI at $0 as the daily driver, Aider at $0–5/month (DeepSeek or free
Gemini models) as the model-agnostic serious-work harness, Amazon Q's free tier (50
requests/month) as the frontier-Claude sampler, and Codex CLI at zero marginal cost if
ChatGPT Plus is already in your stack. Build the Argus-class multi-agent infrastructure on
OpenHands; automate workflows with Goose and Continue.
Why: verified evidence shows the open harnesses reproduce the Claude Code experience —
agentic loop, tool orchestration, context management, git discipline — with a 2–3 point
benchmark spread at the frontier and a 14-point spread within a single harness depending
on the model chosen. The money Claude Code demands buys model capability more than
harness capability, and the model layer is now purchasable piecemeal at far lower prices.
What you give up: frontier Claude reasoning on the hardest 10–15% of problems (novel
architecture, ambiguous deep debugging), Claude Code's most refined context
management and its agent-teams feature, and Anthropic's polish and support. All of that is
recoverable selectively — via pay-per-token Anthropic API calls or the 50 Amazon Q requests
— for a few dollars a month instead of $100–200.
The capability-per-rupee ordering is unambiguous: Gemini CLI free → Aider + cheap
models → Amazon Q free → Codex via ChatGPT → selective API → only then, if ever,
Claude Code Max.

## 17 Sources and References

All sources accessed August 8–11, 2026. Repository metadata (stars, license, activity)
verified against the GitHub API on August 8, 2026. Inline citations [n] refer to the numbered
list below.
Primary: official documentation and repositories
[1] Anthropic, "How Claude Code works" — official architecture description of the agentic
loop, sessions, checkpoints, and memory.
[2] Anthropic, "Built-in tools" — Read, Write, Edit, Bash, PowerShell, Grep, Glob, Ripgrep,
LSP, Agent, AskUserQuestion specifications.
[3] Anthropic, "Permissions" — ask/allow/deny model, rule syntax, saved rules.
[4] Anthropic, "MCP in Claude Code" — MCP tool handling and tool search.
[5] Anthropic, "Hooks" — lifecycle events and hook types.
[6] Anthropic, "Skills" — SKILL.md format, levels, bundled skills.
 [7] Anthropic, "Agent SDK overview" — programmable exposure of the agent loop;
commercial terms.
[8] Anthropic, "Claude Code features overview" — extension layer, context-cost
documentation, agent teams.
[9] Aider-AI/aider — GitHub repository, 48,050 stars, Apache-2.0 (verified via GitHub API, Aug
8 2026 ).
[10] Aider, "Model support" — LiteLLM providers, free models, local models, model-class
warnings.
[11] Aider, "Leaderboards" — polyglot benchmark, model cost/latency matrix.
[12] OpenAI Codex CLI — GitHub repository, 104,731 stars, Apache-2.0 (verified ).
[13] OpenAI, "Codex CLI documentation" — commands, subagents, search, skills, cloud.
[14] OpenAI, "Codex approvals & security" — sandbox modes, approval policy, network
proxy.
[15] OpenAI, "Codex skills & plugins".
[16] Google Gemini CLI — GitHub repository (106,417 stars, Apache-2.0, verified ); free-tier
and extension documentation in README and docs.
[17] Gemini CLI documentation. https://google.github.io/gemini-cli/ and
[18] Charm, "Crush" (formerly OpenCode ) — GitHub repository (~27K stars; original
opencode-ai/opencode archived), v0.88.1 Aug 7 2026.
[19] OpenCode/Crush official site — Zen provider access, 75+ providers, privacy posture.
[20] MorphLLM, "The Best AI Coding Agents of 2026" — independent SWE-bench/Terminal-
Bench comparison, Claude Code vs. Codex vs. Antigravity scores, scaffolding analysis, cost
reports.
[21] Cline 

[Section continues in full extracted source text.]
