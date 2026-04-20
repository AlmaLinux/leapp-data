---
name: run-tests
description: >-
  Trigger the AlmaLinux ELevate GitHub Actions workflow (elevate.yml) via the
  `gh` CLI. Use when the user asks to run tests, run the elevate workflow,
  dispatch elevate.yml, or trigger an ELevate CI run.
---

# Run ELevate Tests

Dispatch the `elevate.yml` workflow (`workflow_dispatch`) on GitHub Actions
using the `gh` CLI.

## Prerequisites

- `gh` CLI must be installed and authenticated (`gh auth status`).
- Current directory must be a Git clone of the target repository.

## Workflow

### Step 1: Ensure the `gh` default repository is set

The `gh` CLI needs a default repository for the current directory.

1. Check whether it is set:

   ```bash
   gh repo set-default --view
   ```

   If output contains `no default repository has been set` (or similar),
   continue with step 2. Otherwise the default is already configured — skip
   to Step 2 of the main workflow.

2. Derive the repository from the `origin` remote:

   ```bash
   git remote get-url origin
   ```

   Convert the URL to `<owner>/<repo>` form:
   - `git@github.com:yuravk/leapp-data.git` → `yuravk/leapp-data`
   - `https://github.com/yuravk/leapp-data.git` → `yuravk/leapp-data`

3. Set it:

   ```bash
   gh repo set-default <owner>/<repo>
   ```

### Step 2: Collect the Git ref

By default use the **current branch**:

```bash
git rev-parse --abbrev-ref HEAD
```

Ask the user whether to keep the current branch or pick another ref. Offer:

- current branch (default)
- `devel-ng-0.24.0`
- `devel-ng-0.23.0`
- `devel-ng-0.22.0`
- `devel-ng-0.21.0`

### Step 3: Collect the workflow inputs

Ask the user to confirm or override these inputs. Defaults:

| Input            | Default            | Allowed values                                                                          |
|------------------|--------------------|-----------------------------------------------------------------------------------------|
| `leapp-data-git` | `false`            | `true`, `false`                                                                         |
| `to8`            | `true`             | `true`, `false`                                                                         |
| `to9`            | `true`             | `true`, `false`                                                                         |
| `to10`           | `true`             | `true`, `false`                                                                         |
| `repository`     | `NG (ALBS product)`| `stable`, `stable (ALBS product)`, `testing`, `testing (ALBS product)`, `NG (ALBS product)` |
| `almalinux`      | `true`             | `true`, `false`                                                                         |
| `centos`         | `true`             | `true`, `false`                                                                         |
| `vendors`        | `all`              | `none`, `all`                                                                           |

Use the `AskQuestion` tool when available to collect overrides efficiently.
Accept "use defaults" to skip the question.

### Step 4: Dispatch the workflow

Prefer the JSON-on-stdin form — it handles values containing spaces (like
`NG (ALBS product)`) cleanly:

```bash
echo '{
  "leapp-data-git": "false",
  "to8": "true",
  "to9": "true",
  "to10": "true",
  "repository": "NG (ALBS product)",
  "almalinux": "true",
  "centos": "true",
  "vendors": "all"
}' | gh workflow run elevate.yml --ref <ref> --json
```

Equivalent `-f` form (quote values that contain spaces):

```bash
gh workflow run elevate.yml --ref <ref> \
  -f leapp-data-git=false \
  -f to8=true \
  -f to9=true \
  -f to10=true \
  -f repository="NG (ALBS product)" \
  -f almalinux=true \
  -f centos=true \
  -f vendors=all
```

All input values must be passed as **strings** (`"true"` / `"false"`),
because `workflow_dispatch` inputs are serialized as strings over the API.

### Step 5: Report the dispatched run

`gh workflow run` does not print the run ID. Fetch the most recent run for
`elevate.yml` on the chosen ref:

```bash
gh run list --workflow=elevate.yml --branch <ref> --limit 1 \
  --json databaseId,status,url,headBranch,createdAt
```

Report to the user:
- The run URL
- The ref
- The resolved inputs used

Optionally offer to watch the run:

```bash
gh run watch <run-id>
```

## Triaging failed jobs

When a dispatched run has at least one job with `conclusion != "success"`,
download each failed job's `*-leapp-logs.tar` artifact and inspect the three
leapp log files.

### Step T1: Enumerate failed jobs

```bash
RUN_ID=<run-id>
gh run view "$RUN_ID" --json jobs \
  --jq '.jobs[] | select(.conclusion != "success" and .name != "Set variants matrix") | .name'
```

### Step T2: Map a job name to its artifact name

The workflow uploads artifacts named `<slug>-leapp-logs.tar`, where `<slug>`
is the job name with spaces removed and `to` replaced by `-to-`. Examples:

| Job name                                       | Artifact name                                          |
|-----------------------------------------------|--------------------------------------------------------|
| `centos 9 to centos 10`                       | `centos9-to-centos10-leapp-logs.tar`                   |
| `almalinux 8 to almalinux 9`                  | `almalinux8-to-almalinux9-leapp-logs.tar`              |
| `almalinux 9 to almalinux-kitten 10`          | `almalinux9-to-almalinux-kitten10-leapp-logs.tar`      |
| `almalinux 9 to almalinux-x86_64_v2 10`       | `almalinux9-to-almalinux-x86_64_v210-leapp-logs.tar`   |

When in doubt, list artifacts directly:

```bash
gh api repos/<owner>/<repo>/actions/runs/"$RUN_ID"/artifacts \
  --jq '.artifacts[] | select(.name | endswith("-leapp-logs.tar")) | .name'
```

### Step T3: Download and extract

`gh run download` requires either a git-repo CWD **or** the `-R` flag.
Always pass `-R` to avoid the `not a git repository` failure.

```bash
VARIANT=<artifact-name-without-suffix>   # e.g. centos9-to-centos10
OUT=/tmp/elevate-artifacts/$VARIANT
mkdir -p "$OUT"

gh run download "$RUN_ID" \
  -R <owner>/<repo> \
  -n "${VARIANT}-leapp-logs.tar" \
  -D "$OUT"

tar -xf "$OUT/${VARIANT}-leapp-logs.tar" -C "$OUT"
ls "$OUT/var/log/leapp/"
```

Expected extracted files:

```
var/log/leapp/answerfile
var/log/leapp/answerfile.userchoices
var/log/leapp/dnf-plugin-data.txt
var/log/leapp/leapp-preupgrade.log
var/log/leapp/leapp-report.json
var/log/leapp/leapp-report.txt
var/log/leapp/leapp-upgrade.log
var/log/leapp/archive/leapp-<timestamp>-logs.tar.gz
```

### Step T4: Extract Inhibitor entries from `leapp-report.json`

leapp-report.json entries have these keys: `actor`, `audience`, **`flags`**,
`hostname`, `id`, `key`, `severity`, `summary`, `tags`, `timeStamp`, `title`.
Inhibitors are entries whose `flags` array contains `"inhibitor"`.

```bash
jq '[.entries[]
     | select(.flags and (.flags | index("inhibitor")))
     | {title, severity, summary, actor, key}]' \
  "$OUT/var/log/leapp/leapp-report.json"
```

Also useful — all high-severity entries:

```bash
jq '[.entries[] | select(.severity == "high")
     | {title, summary, flags, actor}]' \
  "$OUT/var/log/leapp/leapp-report.json"
```

#### Severity distribution (human-readable)

Use this formatter to present a sorted, aligned summary with inhibitor
count and percentages. Order is fixed `high → medium → low → info`, and
zero-count rows are kept so readers can see the full picture.

```bash
jq -r '
  {"high":0,"medium":0,"low":0,"info":0} as $order
  | (.entries | length) as $total
  | ([.entries[] | select(.flags // [] | index("inhibitor"))] | length) as $inhib
  | ([.entries[] | .severity] | group_by(.) | map({(.[0]): length}) | add) as $bysev
  | "Total entries: \($total)",
    "Inhibitors:    \($inhib)",
    "",
    (["SEVERITY","COUNT","PERCENT"] | @tsv),
    (["--------","-----","-------"] | @tsv),
    ($order | keys_unsorted[] as $k
       | ($bysev[$k] // 0) as $c
       | [$k, ($c|tostring),
          (if $total>0 then (($c*100/$total)|floor|tostring)+"%" else "-" end)]
       | @tsv)
' "$OUT/var/log/leapp/leapp-report.json" | column -t -s$'\t'
```

Example output:

```
Total entries: 10
Inhibitors:    0

SEVERITY  COUNT  PERCENT
--------  -----  -------
high      3      30%
medium    1      10%
low       0      0%
info      6      60%
```

Include this block at the top of the per-variant report in Step T6 so the
reader gets an at-a-glance picture before the inhibitor details.

#### Per-severity summary

After the distribution table, list every report entry grouped by severity.
This exposes what each row in the table actually is — actor, title, and any
flags (the `inhibitor` flag is the important one to spot here).

```bash
jq -r '
  ["high","medium","low","info"] as $order
  | ([.entries[]] | group_by(.severity)
     | map({(.[0].severity): .}) | add) as $by
  | $order[] as $sev
    | ($by[$sev] // []) as $items
    | "## \($sev | ascii_upcase) (\($items | length))",
      (if ($items | length) == 0 then "  (none)"
       else ($items[]
              | "  - [\(.actor)] \(.title)"
                + (if .flags and (.flags|length)>0
                   then "  [flags: \(.flags|join(","))]"
                   else "" end))
       end),
      ""
' "$OUT/var/log/leapp/leapp-report.json"
```

Example output:

```
## HIGH (3)
  - [check_grub_core] GRUB2 core will be automatically updated during the upgrade
  - [distribution_signed_rpm_check] Packages not signed by the distribution vendor found on the system
  - [report_leftover_packages] Some packages from the original OS have not been upgraded

## MEDIUM (1)
  - [libdb_check] Berkeley DB (libdb) has been detected on your system

## LOW (0)
  (none)

## INFO (6)
  - [check_se_linux] SElinux relabeling will be scheduled
  - [update_grub_core] GRUB core successfully updated
  - …
```

If you also need each entry's **summary** text (multi-line, can be long),
swap the inner line for:

```jq
"  - [\(.actor)] \(.title)\n      \((.summary // "") | gsub("\n";"\n      "))"
```

Keep this extended form for a single variant at a time — it can be
hundreds of lines across the whole matrix.

### Step T5: Extract errors/failures from the leapp log files

leapp logs are Python-logger formatted — severity appears as a standalone
word in the log-level column (e.g. `2026-04-20 12:31:05.937 ERROR PID: ...`).
Anchor the regex on that column to avoid false positives from substrings
like `--errorlevel` or filenames containing `ERROR`.

```bash
# Real log-level lines only: ERROR / CRITICAL / WARNING + Python tracebacks.
PATTERN='(^|\s)(ERROR|CRITICAL|WARNING|Traceback|Exception)(\s|:)'

echo "===== leapp-preupgrade.log ====="
grep -nE "$PATTERN" "$OUT/var/log/leapp/leapp-preupgrade.log" | head -50

echo "===== leapp-upgrade.log ====="
grep -nE "$PATTERN" "$OUT/var/log/leapp/leapp-upgrade.log" | head -50
```

If a `Traceback` line is hit, also dump ~20 lines of context around it:

```bash
grep -nE '^Traceback' "$OUT/var/log/leapp/leapp-upgrade.log" \
  | cut -d: -f1 \
  | while read ln; do
      sed -n "$((ln-2)),$((ln+20))p" "$OUT/var/log/leapp/leapp-upgrade.log"
      echo '---'
    done
```

### Step T6: Report per variant

Produce one block per failed variant:

```
## <variant name>  (job conclusion: <failure|cancelled|…>)

### Severity distribution
<output of the severity-distribution formatter from Step T4>

### Per-severity summary
<output of the per-severity summary formatter from Step T4>

### Inhibitors (leapp-report.json)
- <title> [severity: <sev>] — <summary>
- …

### leapp-preupgrade.log errors
- line <n>: <message>
- …

### leapp-upgrade.log errors
- line <n>: <message>
- …
```

If a section has no hits, write `(none)` — do not omit the section.

## Anti-patterns

- Do **not** pass boolean inputs as bare JSON booleans (`"to8": true`) — use
  the string form (`"to8": "true"`).
- Do **not** omit `--ref` — `gh` then defaults to the repo's default branch,
  which is rarely what the user wants.
- Do **not** skip Step 1. Without a default repo, `gh workflow run` fails
  with `no default remote repository`.
- Do **not** run `gh run download` without `-R <owner>/<repo>` when the CWD
  might not be a git repo — it fails with `fatal: not a git repository`.
- Do **not** filter `leapp-report.json` on a `groups` field — this schema
  uses `flags` (with value `"inhibitor"`).
- Do **not** `grep -i error` on leapp logs — it matches `--errorlevel`,
  filenames like `ERRORS`, etc. Anchor on the Python log-level column.
