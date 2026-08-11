# Director Control Protocol

## The directors

The development director layer is:

- Human operator
- ChatGPT

## Director responsibilities

### Human operator

- operate Claude accounts;
- provide the correct account identity;
- maintain MCP connections;
- manage credentials;
- start/stop work;
- manage GitHub access;
- relay reports;
- execute practical environment actions.

### ChatGPT

- maintain architectural consistency;
- interpret the Bible;
- challenge scope creep;
- review cross-agent decisions;
- determine whether proposed changes are architectural;
- define the next work package;
- help resolve integration disputes.

## Claude authority

Claude owns implementation decisions within its assignment.

The director should not micromanage ordinary implementation details.

## Escalate to director when

- a frozen contract must change;
- architecture is ambiguous;
- a dependency becomes mandatory;
- cost/production feasibility changes materially;
- a security boundary must change;
- two workers disagree about ownership;
- scope needs to expand.

## Do not escalate

Do not interrupt the director for:

- ordinary implementation choices;
- naming;
- helper functions;
- internal refactoring;
- test organization;
- routine dependency updates that preserve architecture.

## Goal

The director layer should remove ambiguity, not become a bottleneck for every line of code.
