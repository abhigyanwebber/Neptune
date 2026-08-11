# Tool Registry

## Tool classes

### Core local
read, write, edit, search, grep, glob, shell, Git, test, build.

### Environment
browser, web fetch/search, package manager, process management.

### External
APIs, databases, cloud services, Git hosting, SaaS.

### Extension
MCP servers.

## Required fields

```yaml
id:
name:
capability:
input_schema:
output_schema:
runtime_requirements:
permissions:
sandbox_requirements:
timeout:
output_limit:
network_access:
side_effects:
risk_class:
provider:
version:
verification_date:
```

## Rule

A tool definition may be deferred. The model should receive capability metadata before full schema where practical.
