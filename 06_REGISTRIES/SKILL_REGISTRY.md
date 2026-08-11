# Skill Registry

A skill is a portable behavior package.

## Required fields

```yaml
id:
name:
purpose:
instructions:
required_capabilities: []
optional_capabilities: []
input_schema:
output_schema:
verification:
security_constraints:
scope:
version:
```

Skills must load dynamically and must not permanently consume model context merely because they exist.
