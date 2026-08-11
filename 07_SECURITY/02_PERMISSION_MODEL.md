# Permission Model

## Four distinct concepts

### Capability
What the runtime can technically do.

### Policy
What the system permits an actor to request.

### Approval
Whether a human or higher-level policy must authorize an action.

### Sandbox
Where/how the action can execute.

## Precedence

```text
GLOBAL DENY
    >
WORKSPACE DENY
    >
TASK DENY
    >
EXPLICIT APPROVAL
    >
ALLOW RULE
```

A deny should prevent capability exposure to the model when practical.

## Example policy

| Action | Default |
|---|---|
| read repository | allow |
| edit workspace | allow |
| run tests | allow |
| install package | ask |
| network access | ask |
| push branch | ask |
| delete remote branch | deny / strong approval |
| production migration | deny / strong approval |
| export secret | deny |

These are initial policy examples, not final production policy.
