---
name: build-and-sign
description: >-
  Build and sign packages on ALBS (AlmaLinux Build System) using the albs-mcp
  MCP server. Use when the user asks to build, rebuild, or sign packages, or
  mentions ALBS builds, or package signing.
---

# Build and Sign Packages

Build leapp-data on ALBS for multiple platforms in a single build, then sign
the completed build with the ELevate key.

## Prerequisites

- The `albs-mcp` MCP server must be running (configured in `.cursor/mcp.json`).
- A valid JWT token must be configured for authenticated operations.

## Workflow

### Step 1: Determine the branch

Get the current git branch to use as the build ref:

```bash
git rev-parse --abbrev-ref HEAD
```

The user may override the branch explicitly. If not, use the current branch.

### Step 2: Create the build

Call `create_build` via the `albs-mcp` MCP server **once** with all platforms
in a single request:

| Parameter   | Value                |
|-------------|----------------------|
| git_urls    | value of `git_urls` (see below) |
| platforms   | `["AlmaLinux-8", "AlmaLinux-9"]` (default, user may override) |
| branch      | current git branch (from Step 1) |
| arch_list   | `["x86_64"]`        |

#### The `git_urls` parameter

The user provides `git_urls` — a list of Git repository URLs pointing to the
project source. This value is passed directly as the `git_urls` argument to
`create_build`.

Examples:
- Upstream: `git_urls=["https://github.com/almalinux/leapp-data.git"]`
- Fork:     `git_urls=["https://github.com/ykohut/leapp-data.git"]`

If the user does not supply `git_urls`, ask them for the Git repository URL
before proceeding.

Record the returned **build ID**.

### Step 3: Wait for the build to complete

Poll the build with `get_build_info` until all tasks show `completed` or `failed`.
Use exponential backoff: start at 60 seconds, increase up to 5 minutes between checks.

If any task **fails**, report the failure to the user and ask whether to proceed
with signing or investigate the failure.

### Step 4: Sign the build

Once the build has completed successfully, call `sign_build` with:

| Parameter   | Value |
|-------------|-------|
| build_id    | the build ID from Step 2 |
| sign_key_id | `3` (ELevate key) |

### Step 5: Report results

Present a summary:

```
| Build ID | Platforms                    | Build Status | Sign Task ID | Sign Status |
|----------|------------------------------|--------------|--------------|-------------|
| ...      | AlmaLinux-8, AlmaLinux-9     | completed    | ...          | idle        |
```

Include the build URL: `https://build.almalinux.org/build/<build_id>`
