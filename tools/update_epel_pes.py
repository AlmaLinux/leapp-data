#!/usr/bin/env python3
"""Update vendors.d/epel_pes.json_template by diffing EPEL repodata across majors.

For each requested upgrade path the script:
  1. Downloads (and caches) repomd.xml + primary.xml.gz for each relevant repo
     (EPEL on both sides, plus EL7 base/extras for the 7to8 path).
  2. Builds per-arch indexes of binary package names and the reverse Obsoletes
     graph from the target side.
  3. Synthesizes PES events:
       - REPLACED/SPLIT/MERGED (3/4/5) when target Obsoletes a
         source-side name - and only if the source-side name is itself
         absent on the target side. Per-target grouping decides the
         action: 1 source -> 1 target = REPLACED; 1 source -> N targets
         = SPLIT; N >= 2 sources -> any targets = MERGED (e.g. EPEL 9
         `tmt` Obsoletes the four `tmt-report-*` subpackages, which
         collapses to one MERGED instead of four REPLACED). When the
         source name still exists on the target side, dnf will upgrade
         it in place; any sibling Obsoletes is treated as a soft hygiene
         marker (e.g. NetworkManager-openconnect-gnome carrying
         `Obsoletes: NetworkManager-openconnect < ...`) and is
         deliberately not turned into a PES event.
       - REMOVED (1) when the source-side name is gone on the target side -
         OFF BY DEFAULT. EPEL (especially EL10) is still being populated by
         maintainers, so a missing target package today is often "not yet
         packaged" rather than "permanently dropped". Emitting REMOVED
         would have leapp uninstall those packages during the upgrade.
         Pass --include-removed (or set DEFAULT_INCLUDE_REMOVED=True below)
         to re-enable emitting them.
       - MOVED (6) when the same name exists on both sides (repo move) -
         OFF BY DEFAULT. dnf already finds the package in the new repo
         (e.g. `el10-epel`), so a PES event is redundant for these. Pass
         --include-moved (or set DEFAULT_INCLUDE_MOVED=True below) to
         re-enable emitting them.
  4. Merges results into vendors.d/epel_pes.json_template in place: signature
     matches refresh only architectures, fresh events get newly allocated
     id/set_id values that are unique across every *pes*.json* in the tree.
  5. Refreshes the file's timestamp + provided_data_streams, then runs the
     schema and dup-id validators against the whole tree.

CLI:
    update_epel_pes.py [--paths 7to8,8to9,9to10] [--archs ...]
                       [--cache-dir DIR] [--dry-run] [--force]
                       [--include-moved] [--include-removed]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import json
import lzma
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import requests
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
TEMPLATE_PATH = os.path.join(REPO_ROOT, 'vendors.d', 'epel_pes.json_template')
SCHEMA_PATH = os.path.join(REPO_ROOT, 'tests', 'pes-events-schema.json')
DEFAULT_CACHE = os.path.join(HERE, '.cache', 'repodata')

DEFAULT_ARCHS = ('x86_64', 'aarch64', 'ppc64le', 's390x')

# Whether to emit MOVED (6) events for packages that exist with the same name
# in both the source and target EPEL repos. Empirically these events are not
# needed: dnf finds the package in the new repo (e.g. `el10-epel`) without a
# PES hint, so the events would just bloat the template. Flip this to True
# (or pass --include-moved on the CLI) to re-enable them.
DEFAULT_INCLUDE_MOVED = False

# Whether to emit REMOVED (1) events for source-side names that have no
# successor in the target EPEL repo (no same-name package, no Obsoletes
# claimant). EPEL - especially EL10 - is continuously growing as maintainers
# rebuild their packages, so a name that is "missing today" is more often
# "not yet packaged" than "permanently dropped". Emitting REMOVED would have
# leapp uninstall those packages during the upgrade, which is usually too
# aggressive for vendor PES data. Flip this to True (or pass --include-removed
# on the CLI) to re-enable them.
DEFAULT_INCLUDE_REMOVED = False

# Initial/release minor anchors. Match what is already used in the template
# (CentOS 7.9 -> 8.x for the 7to8 path; .0 elsewhere).
PATH_RELEASES = {
    '7to8': {'initial': (7, 9), 'release': (8, 0)},
    '8to9': {'initial': (8, 0), 'release': (9, 0)},
    '9to10': {'initial': (9, 0), 'release': (10, 0)},
}

# Output PESID per upgrade path.
TARGET_PESID = {
    '7to8': 'el8-epel',
    '8to9': 'el9-epel',
    '9to10': 'el10-epel',
}


# ---------------------------------------------------------------------------
# Repodata sources
# ---------------------------------------------------------------------------


@dataclass
class RepoSource:
    """One repository (one arch) we fetch primary.xml from."""

    label: str            # human-readable, used for cache filename and logs
    pesid: str            # PES ID used in the generated event
    arch: str             # x86_64 / aarch64 / ppc64le / s390x
    base_url: str         # ends with the repodata's parent dir (no trailing /)
    side: str             # "source" or "target"


def epel_archive_url(arch: str) -> str:
    return f'https://archives.fedoraproject.org/pub/archive/epel/7/{arch}'


def epel_active_url(major: int, arch: str) -> str:
    # EPEL 10 ships under /pub/epel/10z/ (the "z-stream" feed that tracks
    # released RHEL 10 minors), not /pub/epel/10/ (which currently mirrors
    # ELN-tracking content). For older majors keep /pub/epel/<N>/.
    branch = '10z' if major == 10 else str(major)
    return f'https://dl.fedoraproject.org/pub/epel/{branch}/Everything/{arch}'


def centos7_vault_url(component: str) -> str:
    # component: 'os' for base, 'extras' for extras. EL7 mainstream was x86_64.
    return f'https://vault.centos.org/7.9.2009/{component}/x86_64'


def sources_for_path(path: str, archs: Iterable[str]) -> List[RepoSource]:
    archs = list(archs)
    out: List[RepoSource] = []

    if path == '7to8':
        for a in archs:
            if a != 'x86_64':
                continue
            out.append(RepoSource('epel7', 'epel', a, epel_archive_url(a), 'source'))
        out.append(RepoSource('centos7-base', 'base', 'x86_64',
                              centos7_vault_url('os'), 'source'))
        out.append(RepoSource('centos7-extras', 'extras', 'x86_64',
                              centos7_vault_url('extras'), 'source'))
        for a in archs:
            out.append(RepoSource(f'epel8-{a}', 'el8-epel', a,
                                  epel_active_url(8, a), 'target'))
    elif path == '8to9':
        for a in archs:
            out.append(RepoSource(f'epel8-{a}', 'epel', a,
                                  epel_active_url(8, a), 'source'))
            out.append(RepoSource(f'epel9-{a}', 'el9-epel', a,
                                  epel_active_url(9, a), 'target'))
    elif path == '9to10':
        for a in archs:
            out.append(RepoSource(f'epel9-{a}', 'epel', a,
                                  epel_active_url(9, a), 'source'))
            out.append(RepoSource(f'epel10-{a}', 'el10-epel', a,
                                  epel_active_url(10, a), 'target'))
    else:
        raise ValueError(f'Unknown upgrade path: {path}')
    return out


# ---------------------------------------------------------------------------
# Fetch + cache + parse
# ---------------------------------------------------------------------------


REPOMD_NS = '{http://linux.duke.edu/metadata/repo}'
COMMON_NS = '{http://linux.duke.edu/metadata/common}'
RPM_NS = '{http://linux.duke.edu/metadata/rpm}'


_HTTP_HEADERS = {'User-Agent': 'leapp-data update_epel_pes.py'}


def _fetch(url: str, dest_path: str) -> None:
    """Download `url` into `dest_path`."""
    print(f'  fetching {url}')
    tmp = dest_path + '.part'
    try:
        with requests.get(url, headers=_HTTP_HEADERS, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(tmp, 'wb') as fh:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        fh.write(chunk)
    except requests.RequestException as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f'HTTP error fetching {url}: {e}') from e
    os.replace(tmp, dest_path)


def _ensure_cached(repo: RepoSource, cache_dir: str) -> str:
    """Ensure repomd.xml + primary.xml.gz are cached. Return primary path."""
    repo_cache = os.path.join(cache_dir, repo.label)
    os.makedirs(repo_cache, exist_ok=True)

    repomd_path = os.path.join(repo_cache, 'repomd.xml')
    if not os.path.exists(repomd_path):
        _fetch(f'{repo.base_url}/repodata/repomd.xml', repomd_path)

    repomd = ET.parse(repomd_path).getroot()
    primary_href = None
    for data in repomd.findall(f'{REPOMD_NS}data'):
        if data.get('type') == 'primary':
            loc = data.find(f'{REPOMD_NS}location')
            if loc is not None:
                primary_href = loc.get('href')
            break
    if not primary_href:
        raise RuntimeError(f'Could not find primary in {repomd_path}')

    primary_basename = os.path.basename(primary_href)
    primary_path = os.path.join(repo_cache, primary_basename)
    if not os.path.exists(primary_path):
        _fetch(f'{repo.base_url}/{primary_href}', primary_path)
    return primary_path


@dataclass
class PackageInfo:
    """Minimal per-binary-package info we keep from primary.xml."""

    name: str
    arch: str
    obsoletes: List[str] = field(default_factory=list)


@dataclass
class RepoIndex:
    pesid: str
    side: str
    # name -> set of arches where it's present
    name_to_arches: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    # name -> set of obsoleting names, aggregated across arches
    obsoleted_by: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))


def _decompress_zst(path: str) -> str:
    """Decompress a .zst file to a sibling .xml file once, return its path."""
    if not path.endswith('.zst'):
        return path
    out_path = path[:-len('.zst')]
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    # Try python modules first (avoid spawning a subprocess if possible).
    try:
        import zstandard  # type: ignore
        dctx = zstandard.ZstdDecompressor()
        with open(path, 'rb') as src, open(out_path + '.part', 'wb') as dst:
            dctx.copy_stream(src, dst)
        os.replace(out_path + '.part', out_path)
        return out_path
    except ImportError:
        pass
    try:
        import pyzstd  # type: ignore
        with open(path, 'rb') as src, open(out_path + '.part', 'wb') as dst:
            pyzstd.decompress_stream(src, dst)
        os.replace(out_path + '.part', out_path)
        return out_path
    except ImportError:
        pass
    # Fall back to the system zstd / unzstd CLI.
    for cmd in (['zstd', '-d', '-q', '-f', path, '-o', out_path],
                ['unzstd', '-q', '-f', path, '-o', out_path]):
        try:
            subprocess.check_call(cmd)
            return out_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError(
        f'Cannot decompress {path}: install the python "zstandard" package '
        f'or the "zstd" CLI tool')


def _open_primary(path: str):
    if path.endswith('.zst'):
        path = _decompress_zst(path)
    if path.endswith('.gz'):
        return gzip.open(path, 'rb')
    if path.endswith('.xz'):
        return lzma.open(path, 'rb')
    return open(path, 'rb')


def _parse_primary(primary_path: str, arch: str) -> Iterable[PackageInfo]:
    """Yield PackageInfo for every <package type="rpm"> in the primary.xml feed."""
    with _open_primary(primary_path) as fh:
        # iterparse keeps memory bounded for huge feeds.
        for event, elem in ET.iterparse(fh, events=('end',)):
            if elem.tag != f'{COMMON_NS}package':
                continue
            if elem.get('type') != 'rpm':
                elem.clear()
                continue
            name_el = elem.find(f'{COMMON_NS}name')
            arch_el = elem.find(f'{COMMON_NS}arch')
            if name_el is None or arch_el is None:
                elem.clear()
                continue
            pkg_name = name_el.text or ''
            pkg_arch = arch_el.text or ''
            # Skip srpms and noarch metapackages we don't need? No: noarch
            # binary RPMs ARE real packages users install; they should be
            # tracked. We do skip src arch since SRPMs aren't installable.
            if pkg_arch == 'src':
                elem.clear()
                continue

            obsoletes: List[str] = []
            fmt = elem.find(f'{COMMON_NS}format')
            if fmt is not None:
                obs_block = fmt.find(f'{RPM_NS}obsoletes')
                if obs_block is not None:
                    for entry in obs_block.findall(f'{RPM_NS}entry'):
                        ent_name = entry.get('name')
                        if ent_name:
                            obsoletes.append(ent_name)

            yield PackageInfo(name=pkg_name, arch=pkg_arch, obsoletes=obsoletes)
            elem.clear()


def build_indexes(repos: List[RepoSource], cache_dir: str) -> Dict[Tuple[str, str], RepoIndex]:
    """Return (pesid, side) -> RepoIndex aggregated over arches."""
    indexes: Dict[Tuple[str, str], RepoIndex] = {}

    for repo in repos:
        print(f'[{repo.side}] {repo.label} ({repo.pesid}, {repo.arch})')
        primary = _ensure_cached(repo, cache_dir)
        key = (repo.pesid, repo.side)
        idx = indexes.setdefault(key, RepoIndex(pesid=repo.pesid, side=repo.side))

        # Track names seen in this arch so we record arch presence even when
        # the package never appears in another arch's primary.
        seen_arches_for_name: Dict[str, Set[str]] = defaultdict(set)

        for pkg in _parse_primary(primary, repo.arch):
            seen_arches_for_name[pkg.name].add(repo.arch)
            idx.name_to_arches[pkg.name].add(repo.arch)
            for obs in pkg.obsoletes:
                # On the target side this gives us "obs is obsoleted by pkg".
                idx.obsoleted_by[obs].add(pkg.name)

    return indexes


# ---------------------------------------------------------------------------
# Event synthesis
# ---------------------------------------------------------------------------


@dataclass
class SynthEvent:
    action: int
    initial_major: int
    initial_minor: int
    release_major: int
    release_minor: int
    architectures: List[str]
    in_pkgs: List[Tuple[str, str]]   # (name, pesid)
    out_pkgs: List[Tuple[str, str]]  # (name, pesid); empty = REMOVED


def _sorted_archs(archs: Iterable[str]) -> List[str]:
    """Match the order used in the existing template."""
    order = ['x86_64', 'aarch64', 'ppc64le', 's390x']
    arch_set = set(archs)
    return [a for a in order if a in arch_set]


def synthesize(path: str,
               source_indexes: Dict[str, RepoIndex],
               target_index: RepoIndex,
               include_moved: bool = DEFAULT_INCLUDE_MOVED,
               include_removed: bool = DEFAULT_INCLUDE_REMOVED) -> List[SynthEvent]:
    """Compute new events for one upgrade path.

    `source_indexes`: pesid -> RepoIndex (one per source-side PESID).
    `target_index`: the single target-side RepoIndex (one PESID).
    `include_moved`: when False (default), skip the same-name repo-move case
        that would otherwise emit action=6 MOVED events; dnf can resolve those
        without a PES hint, so the events are redundant.
    `include_removed`: when False (default), skip the source-only case that
        would otherwise emit action=1 REMOVED events. EPEL (especially EL10)
        is still being populated; a missing target package is often a
        not-yet-rebuilt one rather than a permanently dropped one, so we
        prefer not to instruct leapp to uninstall it.
    """

    rels = PATH_RELEASES[path]
    target_pesid = TARGET_PESID[path]
    events: List[SynthEvent] = []

    # Build a flat "name -> set(source-pesids)" view to know which input PESID
    # the package came from.
    name_to_source_pesids: Dict[str, Set[str]] = defaultdict(set)
    name_to_source_arches: Dict[str, Set[str]] = defaultdict(set)
    for pesid, idx in source_indexes.items():
        for name, arches in idx.name_to_arches.items():
            name_to_source_pesids[name].add(pesid)
            name_to_source_arches[name].update(arches)

    # For deciding whether a source-side name is "covered" by an obsoleter.
    obsoleter_of: Dict[str, Set[str]] = target_index.obsoleted_by

    target_names = set(target_index.name_to_arches.keys())

    # Track which source names have been emitted via Obsoletes already,
    # so we don't also create a same-name repo-move event for them.
    handled_via_obsoletes: Set[str] = set()

    # 1) Obsoletes-driven REPLACED / SPLIT / MERGED.
    #
    # We do this in two passes:
    #
    #   1a. Per-source-name pass: for each source-side name that is gone on
    #       the target side, look up which target packages declare
    #       `Obsoletes: <src_name>`. Filter out non-real obsoleters
    #       (target_names membership, self-Obsoletes hygiene markers).
    #
    #   1b. Group those candidates by their (sorted) target packageset.
    #       When N >= 2 distinct source names share the same target set
    #       this is a textbook MERGED (action=5): multiple source
    #       packages converging into the same successor (e.g. EPEL 9
    #       `tmt` Obsoletes the four `tmt-report-*` subpackages). When
    #       N == 1 fall back to the per-target-count classification:
    #       1 obsoleter -> REPLACED (3); >=2 obsoleters -> SPLIT (4).
    #
    # MERGED is preferred over a fan-out of N REPLACED because (a) it
    # records the consolidation as one decision, and (b) leapp triggers
    # MERGED with any-of semantics (event applies if any in_pkg is
    # installed), matching how subpackage consolidations actually behave.
    candidates: List[Tuple[str, Tuple[str, ...], Set[str]]] = []
    for src_name, source_pesids in sorted(name_to_source_pesids.items()):
        # If the source name itself still exists on the target side, the
        # canonical successor is "the same package, just from the new repo"
        # and dnf will upgrade it in place. Any other package carrying an
        # `Obsoletes: <src_name>` line is almost always a soft hygiene
        # marker (subpackage Obsoletes its old monolithic name, sibling
        # subpackage carries a versioned `< X.Y` cleanup, ...). Treating
        # those as REPLACED / SPLIT / MERGED would force-pull the
        # obsoleter (e.g. NetworkManager-openconnect ->
        # NetworkManager-openconnect-gnome), which is exactly the
        # over-aggressive behaviour we want vendor PES data to avoid.
        # Skip and let the same-name MOVED branch handle it (skipped by
        # default; --include-moved to re-enable).
        if src_name in target_names:
            continue

        obsoleters = sorted(obsoleter_of.get(src_name, set()))
        # Only consider obsoleters that actually exist in the target index;
        # otherwise we'd be inventing target packages.
        obsoleters = [o for o in obsoleters if o in target_names]
        if not obsoleters:
            continue
        # Defensive: a package can only Obsolete its own old name if the
        # current name is also gone, which the check above already filtered.
        obsoleters = [o for o in obsoleters if o != src_name]
        if not obsoleters:
            continue

        candidates.append((src_name, tuple(obsoleters), set(source_pesids)))
        handled_via_obsoletes.add(src_name)

    # Group candidates by target packageset (the obsoleter tuple).
    by_target_set: Dict[Tuple[str, ...], List[Tuple[str, Set[str]]]] = defaultdict(list)
    for src_name, obs_tuple, source_pesids in candidates:
        by_target_set[obs_tuple].append((src_name, source_pesids))

    for obs_tuple, src_list in sorted(by_target_set.items()):
        # Sort source names for deterministic in_pkgs ordering (drives the
        # event signature used by the in-place merger).
        src_list = sorted(src_list, key=lambda item: item[0])
        in_pkgs = [(name, _pick_source_pesid(pesids)) for name, pesids in src_list]
        out_pkgs = [(o, target_pesid) for o in obs_tuple]

        if len(src_list) >= 2:
            action = 5  # MERGED (any-of in_pkgs triggers, all in_pkgs removed)
        elif len(obs_tuple) == 1:
            action = 3  # REPLACED (1 -> 1)
        else:
            action = 4  # SPLIT (1 -> N)

        # Architectures: union over every source name in the group.
        arch_set: Set[str] = set()
        for src_name, _pesids in src_list:
            arch_set.update(name_to_source_arches[src_name])

        events.append(SynthEvent(
            action=action,
            initial_major=rels['initial'][0],
            initial_minor=rels['initial'][1],
            release_major=rels['release'][0],
            release_minor=rels['release'][1],
            architectures=_sorted_archs(arch_set),
            in_pkgs=in_pkgs,
            out_pkgs=out_pkgs,
        ))

    # 2) Same-name repo move (action 6) and 3) REMOVED (action 1).
    for src_name, source_pesids in sorted(name_to_source_pesids.items()):
        if src_name in handled_via_obsoletes:
            continue
        in_pesid = _pick_source_pesid(source_pesids)
        if src_name in target_names:
            # Same-name, present in both source and target. dnf already
            # resolves this without a PES event (verified empirically with
            # the `3cpio` package on AlmaLinux 9->10), so skip by default.
            # Re-enable via include_moved=True / --include-moved.
            if not include_moved:
                continue
            events.append(SynthEvent(
                action=6,
                initial_major=rels['initial'][0],
                initial_minor=rels['initial'][1],
                release_major=rels['release'][0],
                release_minor=rels['release'][1],
                architectures=_sorted_archs(name_to_source_arches[src_name]),
                in_pkgs=[(src_name, in_pesid)],
                out_pkgs=[(src_name, target_pesid)],
            ))
        else:
            # Source-only: no same-name target package, no Obsoletes claimant.
            # Skip by default - EPEL (esp. EL10) is still filling out, so a
            # missing package today is often "not yet rebuilt" rather than
            # "permanently dropped". Re-enable via include_removed=True /
            # --include-removed.
            if not include_removed:
                continue
            events.append(SynthEvent(
                action=1,
                initial_major=rels['initial'][0],
                initial_minor=rels['initial'][1],
                release_major=rels['release'][0],
                release_minor=rels['release'][1],
                architectures=_sorted_archs(name_to_source_arches[src_name]),
                in_pkgs=[(src_name, in_pesid)],
                out_pkgs=[],
            ))

    return events


def _pick_source_pesid(pesids: Set[str]) -> str:
    # Prefer 'epel' when present, then 'extras', then 'base', then anything.
    for preferred in ('epel', 'extras', 'base'):
        if preferred in pesids:
            return preferred
    return sorted(pesids)[0]


# ---------------------------------------------------------------------------
# Template I/O + in-place merge
# ---------------------------------------------------------------------------


def _event_signature(event: dict) -> Tuple:
    in_set = event.get('in_packageset') or {}
    out_set = event.get('out_packageset') or {}
    in_pkgs = frozenset(
        (p['name'], p['repository']) for p in (in_set.get('package') or [])
    )
    out_pkgs = frozenset(
        (p['name'], p['repository']) for p in (out_set.get('package') or [])
    )
    init = event.get('initial_release') or {}
    rel = event.get('release') or {}
    return (
        event.get('action'),
        init.get('major_version'),
        rel.get('major_version'),
        in_pkgs,
        out_pkgs,
    )


def _synth_signature(ev: SynthEvent) -> Tuple:
    return (
        ev.action,
        ev.initial_major,
        ev.release_major,
        frozenset(ev.in_pkgs),
        frozenset(ev.out_pkgs),
    )


def _global_id_pools(repo_root: str) -> Tuple[int, int]:
    """Return max(id), max(set_id) across every *pes*.json* in the tree."""
    max_id = 0
    max_set_id = 0
    candidates: List[str] = []
    files_dir = os.path.join(repo_root, 'files')
    vendors_dir = os.path.join(repo_root, 'vendors.d')
    for base in (files_dir, vendors_dir):
        for root, _dirs, names in os.walk(base):
            for n in names:
                if 'pes' in n and ('.json' in n):
                    candidates.append(os.path.join(root, n))
    for path in candidates:
        try:
            with open(path, 'r') as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        for ev in data.get('packageinfo') or []:
            if isinstance(ev.get('id'), int):
                max_id = max(max_id, ev['id'])
            for ps in ('in_packageset', 'out_packageset'):
                pset = ev.get(ps)
                if isinstance(pset, dict) and isinstance(pset.get('set_id'), int):
                    max_set_id = max(max_set_id, pset['set_id'])
    return max_id, max_set_id


class IdAllocator:
    def __init__(self, max_id: int, max_set_id: int) -> None:
        self._next_id = max_id + 1
        self._next_set_id = max_set_id + 1

    def new_id(self) -> int:
        v = self._next_id
        self._next_id += 1
        return v

    def new_set_id(self) -> int:
        v = self._next_set_id
        self._next_set_id += 1
        return v


def _build_event_dict(ev: SynthEvent, allocator: IdAllocator) -> dict:
    """Produce a dict matching the existing template style for a fresh event."""
    in_packages = [
        {
            'module_stream': None,
            'name': name,
            'repository': repo,
        }
        for name, repo in ev.in_pkgs
    ]

    if ev.out_pkgs:
        out_packageset = {
            'package': [
                {
                    'module_stream': None,
                    'name': name,
                    'repository': repo,
                }
                for name, repo in ev.out_pkgs
            ],
            'set_id': allocator.new_set_id(),
        }
    else:
        out_packageset = {
            'package': [],
            'set_id': 0,
        }

    return {
        'action': ev.action,
        'architectures': list(ev.architectures),
        'id': allocator.new_id(),
        'in_packageset': {
            'package': in_packages,
            'set_id': allocator.new_set_id(),
        },
        'initial_release': {
            'major_version': ev.initial_major,
            'minor_version': ev.initial_minor,
            'os_name': '{os_name}',
        },
        'out_packageset': out_packageset,
        'release': {
            'major_version': ev.release_major,
            'minor_version': ev.release_minor,
            'os_name': '{os_name}',
        },
    }


def merge_events(template: dict,
                 synth_events: List[SynthEvent],
                 allocator: IdAllocator) -> Tuple[int, int]:
    """Merge in place. Return (refreshed, appended) counts."""
    existing = template.setdefault('packageinfo', [])
    by_signature: Dict[Tuple, dict] = {}
    for ev in existing:
        by_signature.setdefault(_event_signature(ev), ev)

    refreshed = 0
    appended = 0
    seen_synth: Set[Tuple] = set()

    for synth in synth_events:
        sig = _synth_signature(synth)
        if sig in seen_synth:
            continue
        seen_synth.add(sig)

        existing_event = by_signature.get(sig)
        if existing_event is not None:
            current_archs = existing_event.get('architectures') or []
            merged = sorted(set(current_archs) | set(synth.architectures),
                            key=lambda a: ['x86_64', 'aarch64', 'ppc64le', 's390x'].index(a)
                            if a in ('x86_64', 'aarch64', 'ppc64le', 's390x') else 99)
            if merged != current_archs:
                existing_event['architectures'] = merged
                refreshed += 1
        else:
            existing.append(_build_event_dict(synth, allocator))
            appended += 1

    return refreshed, appended


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _run_validator(args: List[str]) -> int:
    print('+ ' + ' '.join(args))
    return subprocess.call(args, cwd=REPO_ROOT)


def _canonical_validation_files() -> List[str]:
    """Files to validate: one distro's pes-events.json + every vendors.d pes file.

    Mirrors the scope of `check.sh almalinux`. The cross-distro pes-events.json
    files share ids by design (same upstream data), so we only sample one.
    """
    candidates: List[str] = [
        os.path.join(REPO_ROOT, 'files', 'almalinux', 'pes-events.json'),
    ]
    vendors = os.path.join(REPO_ROOT, 'vendors.d')
    for n in sorted(os.listdir(vendors)):
        full = os.path.join(vendors, n)
        if 'pes' in n and '.json' in n and os.path.isfile(full):
            candidates.append(full)
    return candidates


def run_validators() -> bool:
    """Run schema + dup-id checks scoped to the EPEL template's siblings."""
    candidates = _canonical_validation_files()
    rc = _run_validator(['python3', os.path.join('tests', 'validate_json.py'),
                         SCHEMA_PATH, *candidates])
    if rc != 0:
        return False
    rc = _run_validator(['python3', os.path.join('tests', 'validate_ids.py'),
                         *candidates])
    return rc == 0


def _read_almalinux_data_streams() -> Optional[List[str]]:
    path = os.path.join(REPO_ROOT, 'files', 'almalinux', 'pes-events.json')
    try:
        with open(path, 'r') as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    streams = data.get('provided_data_streams')
    if isinstance(streams, list) and streams:
        return list(streams)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    p.add_argument('--paths', default='7to8,8to9,9to10',
                   help='comma-separated upgrade paths (default: %(default)s)')
    p.add_argument('--archs', default=','.join(DEFAULT_ARCHS),
                   help='comma-separated arch list (default: %(default)s)')
    p.add_argument('--cache-dir', default=DEFAULT_CACHE,
                   help='where to cache downloaded repodata (default: %(default)s)')
    p.add_argument('--dry-run', action='store_true',
                   help='do not overwrite the template; write the updated tree to stdout summary only')
    p.add_argument('--force', action='store_true',
                   help='write the template even if validators fail')
    p.add_argument('--include-moved', action='store_true',
                   default=DEFAULT_INCLUDE_MOVED,
                   help='emit action=6 MOVED events for packages whose '
                        'name is unchanged between source and target EPEL '
                        '(default: skipped - dnf already handles them)')
    p.add_argument('--include-removed', action='store_true',
                   default=DEFAULT_INCLUDE_REMOVED,
                   help='emit action=1 REMOVED events for source-side '
                        'packages with no successor in the target EPEL '
                        '(default: skipped - EPEL, especially EL10, is '
                        'still being populated, and REMOVED would have '
                        'leapp uninstall these on upgrade)')
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    paths = [p.strip() for p in args.paths.split(',') if p.strip()]
    for path in paths:
        if path not in PATH_RELEASES:
            print(f'error: unknown path {path!r}; valid: {sorted(PATH_RELEASES)}',
                  file=sys.stderr)
            return 2
    archs = tuple(a.strip() for a in args.archs.split(',') if a.strip())
    os.makedirs(args.cache_dir, exist_ok=True)

    print(f'Loading existing template: {TEMPLATE_PATH}')
    with open(TEMPLATE_PATH, 'r') as fh:
        template = json.load(fh)

    max_id, max_set_id = _global_id_pools(REPO_ROOT)
    print(f'Global id pools: max id={max_id}, max set_id={max_set_id}')
    allocator = IdAllocator(max_id, max_set_id)

    total_refreshed = 0
    total_appended = 0

    for path in paths:
        print(f'\n=== {path} ===')
        repos = sources_for_path(path, archs)
        indexes = build_indexes(repos, args.cache_dir)

        # Split into source-side dict and the single target-side index.
        source_idx: Dict[str, RepoIndex] = {}
        target_idx: Optional[RepoIndex] = None
        for (pesid, side), idx in indexes.items():
            if side == 'source':
                source_idx[pesid] = idx
            else:
                if target_idx is not None and target_idx.pesid != pesid:
                    raise RuntimeError(
                        f'multiple target PESIDs computed for {path}: '
                        f'{target_idx.pesid} vs {pesid}')
                target_idx = idx if target_idx is None else target_idx
        if target_idx is None:
            raise RuntimeError(f'no target index built for {path}')

        synth = synthesize(path, source_idx, target_idx,
                           include_moved=args.include_moved,
                           include_removed=args.include_removed)
        print(f'  synthesized {len(synth)} candidate events '
              f'(MOVED {"included" if args.include_moved else "skipped"}, '
              f'REMOVED {"included" if args.include_removed else "skipped"})')
        refreshed, appended = merge_events(template, synth, allocator)
        print(f'  refreshed {refreshed}, appended {appended}')
        total_refreshed += refreshed
        total_appended += appended

    # Refresh top-level fields.
    template['timestamp'] = _dt.datetime.utcnow().strftime('%Y%m%d%H%MZ')
    streams = _read_almalinux_data_streams()
    if streams:
        template['provided_data_streams'] = streams

    print(f'\nTotals: refreshed={total_refreshed}, appended={total_appended}')

    if args.dry_run:
        print('\n--dry-run: not writing template')
        return 0

    print(f'\nWriting {TEMPLATE_PATH}')
    # Stash a backup OUTSIDE vendors.d so the validators don't pick it up
    # (their glob is "anything with 'pes' and '.json' in the name").
    backup_fd, backup_path = tempfile.mkstemp(prefix='epel_pes_backup_',
                                              suffix='.json',
                                              dir=tempfile.gettempdir())
    try:
        if os.path.exists(TEMPLATE_PATH):
            with open(TEMPLATE_PATH, 'rb') as src, os.fdopen(backup_fd, 'wb') as dst:
                dst.write(src.read())
        else:
            os.close(backup_fd)
        with open(TEMPLATE_PATH, 'w') as fh:
            json.dump(template, fh, indent=4)
            fh.write('\n')

        print('\nRunning validators...')
        ok = run_validators()
        if not ok:
            if args.force:
                print('Validators failed; --force given, keeping the new file.',
                      file=sys.stderr)
                return 1
            print('Validators failed; reverting from backup.', file=sys.stderr)
            with open(backup_path, 'rb') as src, open(TEMPLATE_PATH, 'wb') as dst:
                dst.write(src.read())
            return 1
        return 0
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)


if __name__ == '__main__':
    sys.exit(main())
