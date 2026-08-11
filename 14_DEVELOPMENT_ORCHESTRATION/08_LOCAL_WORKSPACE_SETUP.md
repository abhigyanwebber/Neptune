# Neptune Local Development Workspace Setup

This document describes the recommended local setup for the two-agent development methodology.

## Target layout

```text
C:\Neptune\
├── Neptune-A\
└── Neptune-B\
```

Both folders are independent Git working copies of the same GitHub repository.

## Initial setup

### 1. Initialize the first repository from the final Bible

Extract the final Bible contents directly into:

```text
C:\Neptune\Neptune-A\
```

The repository files should be directly inside that directory.

### 2. Initialize and publish `main`

From `Neptune-A`:

```powershell
git init
git add .
git commit -m "Initialize Neptune infrastructure"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Neptune.git
git push -u origin main
```

### 3. Create Claude A's branch

```powershell
git checkout -b worker/claude-a
git push -u origin worker/claude-a
```

### 4. Create Claude B's independent clone

From the parent directory:

```powershell
cd C:\Neptune
git clone https://github.com/YOUR_USERNAME/Neptune.git Neptune-B
cd Neptune-B
git checkout -b worker/claude-b
git push -u origin worker/claude-b
```

### 5. Verify

Claude A should work from:

```text
Neptune-A → worker/claude-a
```

Claude B should work from:

```text
Neptune-B → worker/claude-b
```

Both should point to the same GitHub repository.

## MCP

Where the MCP filesystem capability allows path scoping:

```text
Claude A → Neptune-A
Claude B → Neptune-B
```

Do not expose the entire parent directory as a writable workspace if it can be avoided.

## Important

This guide does not create GitHub accounts, credentials, branches, MCP connections, or cloud resources automatically. It is a setup reference for the human operator.
