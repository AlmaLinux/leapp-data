# ELevate Data

This repository provides metadata for [ELevate](https://almalinux.org/elevate/) — a project to upgrade between major versions of RHEL-based distributions. The data includes Package Evolution Service (PES) events, repository maps, upgrade repository definitions, and configuration files for multiple target distributions. It also supports 3rd party repositories via the ELevate Vendors mechanism.

## ELevate Core Components

ELevate is built on three core components:

- **[Leapp framework](https://github.com/oamg/leapp)** — the upstream Application & OS Modernization Framework that orchestrates the in-place upgrade process.
- **[AlmaLinux leapp-repository](https://github.com/almalinux/leapp-repository)** — a fork of the upstream leapp-repository containing actors (upgrade workflow steps) adapted for ELevate-supported distributions.
- **leapp-data** (this project) — distribution-specific metadata consumed by the Leapp framework and actors: PES events, repository mappings, upgrade repo definitions, and vendor data.

## Table of Contents

- [RPM Packages (`leapp-data.spec`)](#rpm-packages-leapp-dataspec)
- [Supported Distributions (`files/`)](#supported-distributions-files)
  - [Directory Structure](#directory-structure)
  - [File Descriptions](#file-descriptions)
  - [Contributing to Distributions Data](#contributing-to-distributions-data)
- [3rd Party Repository Support — ELevate Vendors (`vendors.d/`)](#3rd-party-repository-support--elevate-vendors-vendorsd)
  - [Vendor File Structure](#vendor-file-structure)
  - [Contributing a New Vendor](#contributing-a-new-vendor)
- [Tools (`tools/`)](#tools-tools)
- [Tests (`tests/`)](#tests-tests)
- [CI — GitHub Actions (`.github/workflows/elevate.yml`)](#ci--github-actions-githubworkflowselevateyml)
- [License](#license)

---

## RPM Packages (`leapp-data.spec`)

The `leapp-data.spec` file builds all distribution-specific RPM packages from this repository as RPM **subpackages** from a single `rpmbuild` invocation. The list of subpackages produced depends on the builder's major version (`%{?rhel}`):

| RPM Package                              | Built on `%{?rhel}` | Description                                                        |
|------------------------------------------|---------------------|--------------------------------------------------------------------|
| `leapp-data-almalinux`                   | 8, 9                | Metadata for upgrades targeting AlmaLinux                          |
| `leapp-data-almalinux-x86_64_v2`         | 9                   | Metadata for AlmaLinux 9 → AlmaLinux 10 upgrades on **x86-64-v2** hardware |
| `leapp-data-almalinux-kitten`            | 9                   | Metadata for AlmaLinux 9 → AlmaLinux Kitten 10 upgrades             |
| `leapp-data-almalinux-kitten-x86_64_v2`  | 9                   | Metadata for AlmaLinux 9 → AlmaLinux Kitten 10 upgrades on **x86-64-v2** hardware |
| `leapp-data-centos`                      | 8, 9                | Metadata for upgrades targeting CentOS Stream                       |

All `leapp-data-*` packages conflict with each other — only one can be installed at a time, matching the target distribution of the upgrade.

The two `*-x86_64_v2` packages target the AlmaLinux **x86-64-v2 microarchitecture build** of AlmaLinux 10 / Kitten 10, used on hardware that does not meet the default AlmaLinux 10 x86-64-v3 baseline.

### What Gets Installed

Each RPM package installs the following files into the system:

| Destination                                                        | Contents                                                                                                    |
|--------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `/etc/leapp/files/`                                                | `pes-events.json`, `repomap.json`, `leapp_upgrade_repositories.repo`, `device_driver_deprecation_data.json`, `unsupported_driver_names.json`, `unsupported_pci_ids.json` — all from `files/<dist_name>/`, with the version-specific `.el*` suffix stripped to match the source system's major version. |
| `/etc/leapp/files/vendors.d/`                                      | Vendor data: `<vendor>_pes.json`, `<vendor>_map.json`, `<vendor>.repo`, `<vendor>.sigs`, and `vendors.d/rpm-gpg/` GPG keys. Only vendors supported for the given source version are included. |
| `/usr/share/leapp-repository/repositories/system_upgrade/common/files/rpm-gpg/` | Distribution GPG keys (e.g. `RPM-GPG-KEY-AlmaLinux-9`) for target version package signature verification.    |

### Build Process

Since `leapp-data` 0.12, the spec builds every subpackage in a single `rpmbuild` run. Each subpackage's file list is expanded from `%{os_list}`, and each staged file is installed with a `.<os_name>` postfix that RPM strips at install time via `RemovePathPostfixes`.

During the RPM build:

1. **`%build`** — For every `<os_name>` in `%{os_list}`, runs `tools/generate_map_pes_files.sh <os_name> %{?rhel}` against a pristine copy of `vendors.d/`, resolving `{distro}`, `{baseos}`, `{appstream}`, `{powertools}`, and `{os_name}` placeholders into `vendors.d.built.<os_name>/`.
2. **`%install`** — For every `<os_name>`:
   - Copies the corresponding `vendors.d.built.<os_name>/` into a per-dist staging tree.
   - Vendor pruning: removes `epel*` for non-AlmaLinux targets; for `*-x86_64_v2` targets, **keeps only EPEL** and removes every other vendor file.
   - Resolves both generic (`<vendor>.repo.el<ver>`) and per-dist (`<vendor>.repo.el<ver>.<os_name>`) vendor file variants into the final `<vendor>.repo` / `<vendor>.gpg` names.
   - Copies `files/<os_name>/*` and renames the version-specific files (`leapp_upgrade_repositories.repo.el<ver>`, `repomap.json.el<ver>`) to their unversioned names.
   - Installs distribution GPG keys under `%{repositorydir}/system_upgrade/common/files/rpm-gpg/<target_version>/` and `distro/<os_name>/rpm-gpg/<target_version>/`.
   - Moves every staged file into `%{buildroot}` with a `.<os_name>` postfix.
3. **`%check`** — For every `<os_name>`, validates all PES JSON files against the schema (`validate_json.py`), checks for duplicate IDs (`validate_ids.py`), and verifies debranding (`check_debranding.py`).
4. **`%files`** — Auto-generated per subpackage via `%{expand:...}` loop over `%{os_list}`. Each subpackage ships `*.<os_name>` files, which `RemovePathPostfixes: .<os_name>` strips at install time so the files land at their real paths under `/etc/leapp/files/`.

The `x86_64_v2` subpackages are produced only when building on `%{?rhel} == 9`, because AlmaLinux 10 is the only target that exists in an x86-64-v2 microarchitecture build today.

### Supported Vendors per Source Version

The set of included vendors varies by the source system's major version:

| Source EL | Target EL | Vendors                                                                                                       |
|-----------|-----------|---------------------------------------------------------------------------------------------------------------|
| 7         | 8         | epel, imunify, kernelcare, mariadb, nginx-stable, nginx-mainline, postgresql, docker-ce, imunify360-alt-php, tuxcare, elevate |
| 8         | 9         | epel, kernelcare, mariadb, nginx-stable, nginx-mainline, postgresql, docker-ce, tuxcare, elevate               |
| 9         | 10        | epel, imunify, kernelcare, mariadb, nginx-stable, nginx-mainline, docker-ce, postgresql, imunify360-alt-php, tuxcare, elevate |

> **x86_64_v2 exception:** the `leapp-data-almalinux-x86_64_v2` and `leapp-data-almalinux-kitten-x86_64_v2` subpackages ship **EPEL only** — all other vendors are filtered out by the spec at install time. EPEL is included because AlmaLinux provides a dedicated EPEL x86-64-v2 (AltArch) repository for these targets.

---

## Supported Distributions (`files/`)

The `files/` directory contains per-distribution metadata used by the Leapp upgrade framework. Each supported target distribution has its own subfolder:

| Subfolder                         | Description                                                                  |
|-----------------------------------|------------------------------------------------------------------------------|
| `almalinux/`                      | CentOS 7 → AlmaLinux 8, AlmaLinux 8 → 9, AlmaLinux 9 → 10                  |
| `almalinux-x86_64_v2/`            | AlmaLinux 9 → AlmaLinux 10 on **x86-64-v2** hardware (el10 data only)        |
| `almalinux-kitten/`               | AlmaLinux 9 → AlmaLinux Kitten 10                                            |
| `almalinux-kitten-x86_64_v2/`     | AlmaLinux 9 → AlmaLinux Kitten 10 on **x86-64-v2** hardware (el10 data only) |
| `centos/`                         | CentOS 7 → CentOS Stream 8, 8 → 9, 9 → 10                                  |
| `rpm-gpg/`                        | GPG keys for all supported distributions                                     |

The two `*-x86_64_v2` subfolders only ship the el10 versions of `repomap.json` and `leapp_upgrade_repositories.repo` — there is no el8/el9 variant because the x86-64-v2 microarchitecture build only exists for AlmaLinux 10.

### Directory Structure

A typical distribution subfolder (e.g. `almalinux/`) contains:

```
files/almalinux/
├── config.json
├── device_driver_deprecation_data.json
├── leapp_upgrade_repositories.repo.el8
├── leapp_upgrade_repositories.repo.el9
├── leapp_upgrade_repositories.repo.el10
├── pes-events.json
├── repomap.json.el8
├── repomap.json.el9
├── repomap.json.el10
├── unsupported_driver_names.json
└── unsupported_pci_ids.json
```

### File Descriptions

- **`pes-events.json`** — Package Evolution Service events. Describes what happens to each package during the upgrade: removed (action `1`), replaced (action `3`), split, merged (action `5`), moved to a different repository (action `6`), etc. Each entry specifies the source package, target package, architectures, source/target OS versions, and repository mappings.

- **`repomap.json.el{8,9,10}`** — Repository mapping files (one per target major version). They define how source-system repositories map to target-system repositories. For example, the CentOS 7 `base` repo maps to `almalinux8-baseos`, `almalinux8-appstream`, `almalinux8-powertools`, and other AlmaLinux 8 repos.

- **`leapp_upgrade_repositories.repo.el{8,9,10}`** — Yum/DNF `.repo` files defining the target system's upgrade repositories (mirrorlists, GPG keys, etc.).

- **`config.json`** — Distribution-specific configuration. Includes OS name mappings, repository replacing rules (mapping RHEL repository IDs to distro-specific ones), package replacing/debranding rules (e.g. `redhat-release` → `almalinux-release`), removable packages and repositories, and additional PES actions.

- **`device_driver_deprecation_data.json`**, **`unsupported_driver_names.json`**, **`unsupported_pci_ids.json`** — Hardware-related data about deprecated/unsupported device drivers and PCI IDs.

### Contributing to Distributions Data

#### Adding or Modifying PES Events

PES events in `pes-events.json` describe how packages transition between OS versions. For example, a **remove** action (action `1`) for the package `empathy` going from CentOS 7.7 to AlmaLinux 8.0:

```json
{
    "action": 1,
    "architectures": ["aarch64", "ppc64le", "s390x", "x86_64"],
    "id": 8,
    "in_packageset": {
        "package": [
            {
                "modulestreams": [null],
                "name": "empathy",
                "repository": "base"
            }
        ],
        "set_id": 12
    },
    "initial_release": {
        "major_version": 7,
        "minor_version": 7,
        "os_name": "CentOS"
    },
    "out_packageset": null,
    "release": {
        "major_version": 8,
        "minor_version": 0,
        "os_name": "AlmaLinux"
    }
}
```

Action types: `0` = Present, `1` = Removed, `2` = Deprecated, `3` = Replaced, `4` = Split, `5` = Merged, `6` = Moved to a different repository.

> **Note:** Each PES event must have a unique `id`, and each packageset must have a unique `set_id`. Use `tools/id_uniquifier.py` to resolve duplicates.

#### Adding or Modifying Upgrade Repositories

The `.repo` files define the target OS repositories used during the upgrade. Example entry from `leapp_upgrade_repositories.repo.el8`:

```ini
[almalinux8-baseos]
name=AlmaLinux $releasever - BaseOS
mirrorlist=https://mirrors.almalinux.org/mirrorlist/$releasever/baseos
# baseurl=https://repo.almalinux.org/almalinux/$releasever/BaseOS/$basearch/os/
enabled=1
gpgcheck=0
gpgkey=file:///etc/leapp/repos.d/system_upgrade/common/files/rpm-gpg/8/RPM-GPG-KEY-AlmaLinux-8
```

To contribute a new repository, add a new `[repoid]` section following this format, and ensure the corresponding repository mapping is added to the `repomap.json.el*` files.

---

## 3rd Party Repository Support — ELevate Vendors (`vendors.d/`)

The `vendors.d/` directory provides data for 3rd party repositories that need to be preserved or upgraded alongside the base OS. Currently supported vendors include:

| Vendor                | Description                              |
|-----------------------|------------------------------------------|
| `docker-ce`           | Docker Community Edition                 |
| `elevate`             | ELevate project packages                 |
| `epel`                | Extra Packages for Enterprise Linux      |
| `imunify`             | Imunify360 security suite                |
| `imunify360-alt-php`  | Imunify360 alternative PHP packages      |
| `kernelcare`          | KernelCare live patching                 |
| `mariadb`             | MariaDB database server                  |
| `microsoft`           | Microsoft Linux packages (Azure CLI)     |
| `nginx-mainline`      | Nginx mainline branch                    |
| `nginx-stable`        | Nginx stable branch                      |
| `postgresql`          | PostgreSQL database server               |
| `tuxcare`             | TuxCare extended support                 |

### Vendor File Structure

Each vendor is defined by a set of files following the naming convention `<vendor>_<type>.<suffix>`:

| File Pattern                            | Purpose                                                                                     |
|-----------------------------------------|---------------------------------------------------------------------------------------------|
| `<vendor>_pes.json` or `<vendor>_pes.json_template` | PES events for vendor packages (describes package transitions during upgrade). Templates contain `{os_name}` placeholders. |
| `<vendor>_map.json_template.el{8,9,10}` | Repository mapping templates for each target version. Contains `{distro}`, `{baseos}`, `{appstream}`, `{powertools}` placeholders that are resolved per distribution at build time. |
| `<vendor>.repo.el{8,9,10}`             | Yum/DNF `.repo` files for the vendor's target-version repository.                           |
| `<vendor>.repo.el<ver>.<dist_name>`     | *Per-distribution override* of the above `.repo` file. If present, it takes precedence over the generic `<vendor>.repo.el<ver>` when building the `<dist_name>` package. Used today by EPEL to ship a different repo URL and GPG key for the `almalinux-x86_64_v2` and `almalinux-kitten-x86_64_v2` packages (see `vendors.d/epel.repo.el10.almalinux-x86_64_v2`). |
| `<vendor>.sigs`                         | GPG key signatures (key IDs) used to identify packages from this vendor.                    |

GPG keys for vendors are stored in `vendors.d/rpm-gpg/`. They follow the same suffix convention:

- `<vendor>.gpg.el<ver>` — generic key used for all target distributions at that EL version.
- `<vendor>.gpg.el<ver>.<dist_name>` — per-distribution override (e.g. `epel.gpg.el10.almalinux-x86_64_v2` ships the `RPM-GPG-KEY-AlmaLinux-10-EPEL-AltArch` key used by the x86-64-v2 EPEL repository).

### Contributing a New Vendor

Below is an example based on the **EPEL** vendor showing all required files.

#### 1. Repository file (`epel.repo.el8`)

Define the target repository for each major version you support:

```ini
[el8-epel]
name=Extra Packages for Enterprise Linux 8 - $basearch
#baseurl=https://dl.fedoraproject.org/pub/epel/8/Everything/$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-8&arch=$basearch&infra=$infra&content=$contentdir
enabled=1
gpgcheck=1
countme=1
gpgkey=file:///etc/leapp/files/vendors.d/rpm-gpg/epel.gpg
```

Create similar `.repo.el9` and `.repo.el10` files adjusting the version numbers accordingly.

#### 2. Repository mapping template (`epel_map.json_template.el8`)

Defines how vendor repositories map from source to target, using placeholders:

```json
{
    "datetime": "202506241030Z",
    "version_format": "1.3.0",
    "mapping": [
        {
            "source_major_version": "7",
            "target_major_version": "8",
            "entries": [
                { "source": "epel", "target": ["el8-epel"] },
                { "source": "base", "target": ["el8-epel"] },
                { "source": "epel", "target": ["el8-appstream"] },
                { "source": "epel", "target": ["el8-powertools"] },
                { "source": "epel", "target": ["el8-baseos"] }
            ]
        }
    ],
    "repositories": [
        {
            "pesid": "el8-epel",
            "entries": [
                {
                    "major_version": "8",
                    "repoid": "el8-epel",
                    "arch": "x86_64",
                    "channel": "ga",
                    "repo_type": "rpm",
                    "distro": "{distro}"
                }
            ]
        }
    ],
    "provided_data_streams": ["4.2"]
}
```

The `{distro}`, `{baseos}`, `{appstream}`, and `{powertools}` placeholders are replaced at build time by `tools/generate_map_pes_files.sh` with distribution-specific repository names (e.g. `almalinux8-baseos`, `almalinux8-appstream`).

#### 3. PES events template (`epel_pes.json_template`)

Describes package transitions for vendor packages. Uses `{os_name}` placeholder:

```json
{
    "packageinfo": [
        {
            "action": 6,
            "architectures": ["x86_64", "aarch64", "ppc64le", "s390x"],
            "id": 20476,
            "in_packageset": {
                "package": [
                    { "modulestreams": [null], "name": "GeoIP", "repository": "base" }
                ],
                "set_id": 26991
            },
            "initial_release": { "major_version": 7, "minor_version": 7, "os_name": "CentOS" },
            "out_packageset": {
                "package": [
                    { "module_stream": null, "name": "GeoIP", "repository": "el8-epel" }
                ],
                "set_id": 0
            },
            "release": { "major_version": 8, "minor_version": 9, "os_name": "{os_name}" }
        }
    ]
}
```

#### 4. GPG signatures file (`epel.sigs`)

List vendor GPG key IDs (one per line) used to identify packages from this vendor:

```
21ea45ab2f86d6a1
6a2faea2352c64e5
24c6a8a7f4a80eb5
8a3872bf3228467c
33d98517e37ed158
```

#### 5. GPG key

Place the vendor's GPG public key in `vendors.d/rpm-gpg/<vendor>.gpg`.

---

## Tools (`tools/`)

The `tools/` directory contains helper scripts for generating and updating distribution and vendor data:

| Tool                                    | Description                                                                                     |
|-----------------------------------------|-------------------------------------------------------------------------------------------------|
| `update_pes-events.py`                  | Downloads the upstream PES events from `oamg/leapp-repository`, then applies distribution-specific debranding, package/repository replacements, removals, and additions based on each distro's `config.json`. Generates the final `pes-events.json` for each distribution. |
| `generate_map_pes_files.sh`             | Resolves placeholders (`{distro}`, `{baseos}`, `{appstream}`, `{powertools}`, `{os_name}`) in vendor template files for a given distribution and target major version. Used at build/packaging time. |
| `id_uniquifier.py`                      | Finds and replaces duplicate `id` and `set_id` values across multiple PES JSON files. Ensures uniqueness of identifiers so the Leapp framework processes events correctly. |
| `device_driver_deprecation_data-update.sh` | Downloads upstream device driver deprecation data from `oamg/leapp-repository` and enriches it with AlmaLinux release notes to populate the `available_in_rhel` field for each device. Copies the result to each distribution's `files/` directory. |

---

## Tests (`tests/`)

The `tests/` directory contains validation utilities to ensure data integrity:

| Test                     | Description                                                                                                                                          |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| `validate_json.py`       | Validates PES JSON data files against the JSON Schema (`pes-events-schema.json`). Ensures structural correctness of all `pes-events.json` and vendor PES files. |
| `validate_ids.py`        | Checks for duplicate `id` and `set_id` values across multiple PES JSON files. Reports any collisions that could cause the Leapp framework to misprocess events. |
| `check_debranding.py`    | Scans PES events files for references to Red Hat-specific repository names (`rhel7-`, `rhel8-`, `rhel9-`, `rhel10-`) and package names (`redhat-`) that should have been replaced (debranded) with distribution-specific equivalents. Maintains an exclusion list for packages that legitimately contain `redhat-` in their names (e.g. `redhat-rpm-config`, `redhat-lsb`). |
| `pes-events-schema.json` | JSON Schema (Draft-07) definition used by `validate_json.py` to validate PES events files.                                                           |

---

## CI — GitHub Actions (`.github/workflows/elevate.yml`)

The `elevate.yml` workflow provides end-to-end testing of ELevate upgrades across multiple distribution combinations. It is a **manually triggered** (`workflow_dispatch`) workflow with the following configurable inputs:

| Input              | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `leapp-data-git`   | Build and install `leapp-data` RPM from this Git branch (instead of using the released package). |
| `to8`              | Enable EL7 → EL8 upgrade scenarios.                                        |
| `to9`              | Enable EL8 → EL9 upgrade scenarios.                                        |
| `to10`             | Enable EL9 → EL10 upgrade scenarios.                                       |
| `repository`       | ELevate packages source: `stable`, `testing`, `stable (ALBS product)`, `testing (ALBS product)`, or `NG (ALBS product)`. |
| `almalinux`        | Include AlmaLinux upgrade variants.                                         |
| `centos`           | Include CentOS Stream upgrade variants.                                     |
| `vendors`          | Install 3rd party vendor packages before upgrading: `all` or `none`.        |

### Upgrade Variants

When enabled, the workflow tests these upgrade paths:

- **AlmaLinux:** CentOS 7 → AlmaLinux 8, Scientific Linux 7 → AlmaLinux 8, AlmaLinux 8 → AlmaLinux 9, AlmaLinux 9 → AlmaLinux 10, AlmaLinux 9 → AlmaLinux Kitten 10, AlmaLinux 9 → AlmaLinux **x86_64_v2** 10, AlmaLinux 9 → AlmaLinux **Kitten x86_64_v2** 10
- **CentOS:** CentOS 7 → CentOS Stream 8, CentOS Stream 8 → CentOS Stream 9, CentOS Stream 9 → CentOS Stream 10

### How It Works

1. **Matrix generation** — Builds a dynamic matrix of upgrade variants based on the selected inputs.
2. **VM provisioning** — For each variant, spins up a KVM/libvirt-backed Vagrant VM with the appropriate source OS image.
   - For the `*-x86_64_v2` variants the Vagrantfile sets `v.cpu_mode = "custom"` / `v.cpu_model = "Nehalem"` so the guest only exposes the x86-64-v2 feature baseline (SSE3/SSSE3/SSE4.1/SSE4.2/POPCNT/CMPXCHG16B/LAHF, no AVX/AVX2/BMI/…). `Nehalem` is used because libvirt's `cpu_map` has no entry named `x86-64-v2` (that is a QEMU-only CPU type) and Nehalem's feature set is a clean v2-only equivalent. The CPU model is passed from the workflow to the Vagrantfile via the `vm_cpu_model` env var.
3. **Leapp installation** — Installs Leapp and the upgrade packages from the selected repository. Optionally builds and installs the `leapp-data` RPM from the current Git branch. For the `*-x86_64_v2` targets the workflow also downloads the AlmaLinux 10 `amd64_v2` rootfs tarball (from the `AlmaLinux/container-images` repo, branches `10` and `10-kitten`) into `/etc/leapp/files/rootfs/` so Leapp can bootstrap the target userspace.
4. **Vendor installation** — If vendors are enabled, installs packages from EPEL, KernelCare, Nginx, MariaDB, PostgreSQL, Docker-CE, TuxCare, Imunify360, Microsoft, and linux-firmware. For the `*-x86_64_v2` targets **only EPEL is installed**; every other vendor step is gated by `! contains(env.target_distro, 'x86_64_v2')` and is skipped.
5. **Preupgrade check** — Runs `leapp preupgrade` to identify potential issues.
6. **Inhibitor mitigation** — Automatically mitigates known inhibitors and answers Leapp questions for each source version.
7. **Upgrade** — Runs `leapp upgrade` and reboots the VM to complete the upgrade.
8. **Verification** — Checks that the target OS release string matches expectations, and additionally verifies the architecture of the installed release package: `rpm -qf /etc/almalinux-release` must report `x86_64_v2` for the v2 variants (and `x86_64` for the default ones). Lists any remaining source-version packages.
9. **Artifacts** — Uploads Leapp logs and serial console logs as workflow artifacts for debugging.

---

## License

See the [LICENSE](LICENSE) file for details.
