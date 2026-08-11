# ADR-034 — $0 Baseline Is a Release Gate

## Decision
A Neptune release cannot claim economic viability if it requires temporary credits or paid inference for basic bounded operation.

## Rationale
The research distinguishes durable/free resources from temporary acceleration resources. The architecture must survive the expiration of the latter.

## Consequence
Temporary credits may improve performance but cannot become hidden mandatory dependencies.
