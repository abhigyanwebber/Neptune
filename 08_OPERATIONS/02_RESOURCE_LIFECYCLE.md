# Resource Lifecycle

## Lifecycle

```text
DISCOVERED
   ↓
ELIGIBLE
   ↓
CLAIMED
   ↓
ACTIVE
   ↓
DORMANT
   ↓
EXPIRING
   ↓
EXPIRED
   ↓
REPLACED
```

## Temporary resource rule

Every temporary resource requires:

- activation date;
- expiration date;
- remaining balance;
- intended workload;
- replacement;
- migration/exit plan.

## Azure

Azure student credits are classified as burst capital.

Appropriate uses identified by the research include:

- short GPU experiments if quota is approved;
- temporary high-compute jobs;
- production deployment sprint;
- CI/CD;
- database experiments;
- temporary services.

Every Azure workload needs an exit path:

```text
Azure
 ↓
backup/export
 ↓
alternative resource
 ↓
migration test
 ↓
shutdown
```

## Free backbone

The student research identifies candidate durable layers across:
- Git/CI;
- domains/DNS/CDN;
- frontend;
- APIs;
- databases;
- authentication;
- secrets;
- monitoring;
- free model inference;
- notebooks/GPU;
- persistent CPU;
- scraping.

The exact current offers are tracked as snapshots in the resource registry.
