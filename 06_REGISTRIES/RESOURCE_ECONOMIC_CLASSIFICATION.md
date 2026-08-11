# Resource Economic Classification

This is a classification framework for the resource registry.

It does not assert that a specific provider currently has a specific tier. Current provider facts remain in the research/source material and must be revalidated before activation.

## Required fields for future resource records

```text
resource_id
name
category
economic_class
durability
eligibility
activation_date
expiration_date
quota
criticality
intended_use
replacement
operational_constraints
last_verified
source
```

## Economic classes

| Class | Meaning | Architectural treatment |
|---|---|---|
| C0 | Free and durable | preferred foundation |
| C1 | Free but constrained | foundation only if constraints are acceptable |
| C2 | Temporary credit/trial | burst/experimental capacity |
| C3 | Low recurring cost | justified reliability/capability upgrade |
| C4 | Expensive | exceptional use with explicit approval |

## Durability

| Durability | Meaning |
|---|---|
| durable | no known short activation expiry |
| constrained | free but limited by quota/sleep/capacity |
| temporary | expires or consumes a finite promotional balance |
| unknown | must be verified |

## Criticality

A resource should also be marked:

- optional;
- useful;
- important;
- critical.

A critical resource must have a degradation/replacement strategy.

## Rule

Never infer current eligibility or pricing from this framework. Verify before operational use.
