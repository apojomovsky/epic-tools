"""The tool pin: one upstream tag, the patches on top of it, and the package shape.

Pure. No network, no docker, no writes: ``scripts/build_tool.py`` owns the I/O,
so the rules deciding what a package contains live in one place that tests can
exercise without an upstream checkout or a container.

JSON rather than TOML for the pin file on purpose. The ecosystem's TOML files
are parsed by a hand-rolled reader because the docker toolchain runs Python
3.10 (no ``tomllib``); a pin is read on build hosts and by CI, so the boring
stdlib parser is worth more here than the nicer syntax.
"""

import json
import pathlib
import re

# PlatformIO derives each archive's name and the registry's per-host file set
# from the manifest's ``system`` list, so publishing a token no host owns
# produces a package nobody can install. Windows is one host with several
# spellings, which is why it maps to a list.
KNOWN_SYSTEMS = {
    "linux_x86_64": ["linux_x86_64"],
    "windows_amd64": ["windows_amd64", "windows_x86_64"],
}

BUILD_KINDS = ("make", "python")

# Applied in filename order, so a queue that has to be ordered is numbered by
# whoever added it rather than by directory-read order, which no filesystem
# guarantees.
PATCH_SUFFIXES = (".patch", ".diff")

REQUIRED = (
    "package", "version", "description", "license", "upstream", "build", "systems",
)
_REQUIRED_UPSTREAM = ("url", "page", "tag", "commit", "sha256", "extract_dir")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class PinError(ValueError):
    """A pin file that cannot produce a package. Never raised for I/O."""


def load_pin(path):
    """Parse and validate one pin file. Raises PinError on any problem."""
    path = pathlib.Path(path)
    try:
        data = json.loads(path.read_text())
    except OSError as err:
        raise PinError(f"{path}: cannot read: {err}") from err
    except json.JSONDecodeError as err:
        raise PinError(f"{path}: not valid JSON: {err}") from err
    problems = validate(data)
    if problems:
        raise PinError(f"{path}: " + "; ".join(problems))
    return data


def validate(pin):
    """Every reason this pin cannot build a package, in a stable order."""
    problems = []
    if not isinstance(pin, dict):
        return ["pin must be a JSON object"]
    for field in REQUIRED:
        if field not in pin:
            problems.append(f"missing {field!r}")
    if problems:
        return problems

    if not str(pin["version"]).strip():
        problems.append("version is empty")
    license_spec = pin["license"]
    if not isinstance(license_spec, dict) or not license_spec.get("file"):
        problems.append("license must name the upstream file it ships")
    elif not license_spec.get("spdx") and not license_spec.get("name"):
        # PlatformIO validates the manifest's license against the SPDX list, so
        # a licence with no identifier (Microchip's PK2CMD) carries its name
        # instead and the manifest field is left out.
        problems.append("license needs an spdx id or a name")

    upstream = pin["upstream"]
    if not isinstance(upstream, dict):
        problems.append("upstream must be an object")
    else:
        for field in _REQUIRED_UPSTREAM:
            if not str(upstream.get(field, "")).strip():
                problems.append(f"upstream.{field} is empty")
        digest = str(upstream.get("sha256", ""))
        if digest and not _SHA256.fullmatch(digest):
            problems.append("upstream.sha256 is not a lowercase hex sha256")

    build = pin["build"]
    if not isinstance(build, dict) or build.get("kind") not in BUILD_KINDS:
        problems.append(f"build.kind must be one of {', '.join(BUILD_KINDS)}")
    elif build["kind"] == "make" and not build.get("output"):
        problems.append("a make build must name its built binary in build.output")

    systems = pin["systems"]
    if not isinstance(systems, list) or not systems:
        problems.append("systems must be a non-empty list")
    else:
        for system in systems:
            if system not in KNOWN_SYSTEMS:
                problems.append(f"unknown system {system!r}")
    for library in pin.get("bundled_libraries", []):
        if not str(library).strip():
            problems.append("bundled_libraries entries must be names")
    if pin.get("notice") is not None and not str(pin["notice"]).strip():
        problems.append("notice is present but empty")
    destinations = set()
    for index, data in enumerate(pin.get("data_files", [])):
        problems += _data_file_problems(index, data)
        if isinstance(data, dict) and data.get("to"):
            # Staged in order, so a repeated destination would silently let a
            # later entry replace the file an earlier one pinned.
            to = pathlib.PurePosixPath(str(data["to"])).as_posix()
            if to in destinations:
                problems.append(f"data_files[{index}] repeats destination {to!r}")
            destinations.add(to)
    return problems


def _data_file_problems(index, data):
    """A data file comes from the upstream tree or from its own pinned URL.

    The second form exists for data upstream ships but we must not: pk2cmd's
    own PK2DeviceFile.dat is under a third-party copyright claim, so the
    package carries Microchip's file from a separate, digest-checked source.
    """
    where = f"data_files[{index}]"
    if not isinstance(data, dict) or not str(data.get("to", "")).strip():
        return [f"{where} must be an object naming its destination in 'to'"]
    has_from, has_url = bool(data.get("from")), bool(data.get("url"))
    if has_from == has_url:
        return [f"{where} needs exactly one of 'from' (upstream tree) or 'url'"]
    if has_url and not _SHA256.fullmatch(str(data.get("sha256", ""))):
        return [f"{where} fetched by url needs a lowercase hex sha256"]
    if has_url and not str(data.get("origin", "")).strip():
        # The upstream archive's provenance is its tag and commit; a file
        # fetched on its own has only this line in SOURCE.txt to carry it.
        return [f"{where} fetched by url needs an origin naming what it is"]
    return []


def pinned_data_files(pin):
    """The data files fetched from their own URL rather than the upstream tree."""
    return [data for data in pin.get("data_files", []) if data.get("url")]


def patch_queue(pin_dir):
    """The patch files to apply, in filename order.

    An empty queue is the design's success state, not an unfinished one: a
    pin only grows a patch when the change has not reached upstream yet.
    """
    patch_dir = pathlib.Path(pin_dir) / "patches"
    if not patch_dir.is_dir():
        return []
    return sorted(
        path for path in patch_dir.iterdir()
        if path.is_file() and path.suffix in PATCH_SUFFIXES
    )


def archive_name(pin, system, version=None):
    """The PlatformIO archive name for one host: <package>-<system>-<version>."""
    resolved = version or pin["version"]
    return f"{pin['package']}-{system}-{resolved}.tar.gz"


def systems_of(pin, system):
    """The manifest's ``system`` list for one build host."""
    return KNOWN_SYSTEMS[system]


def manifest(pin, system, version=None):
    """The package.json PlatformIO reads, minus what the caller fills in."""
    data = {
        "name": pin["package"],
        "version": version or pin["version"],
        "description": pin["description"],
        "system": systems_of(pin, system),
        "homepage": pin["upstream"]["page"],
        "repository": pin.get("repository") or {
            "type": "git", "url": pin["upstream"]["page"],
        },
    }
    if pin.get("keywords"):
        data["keywords"] = list(pin["keywords"])
    spdx = pin["license"].get("spdx")
    if spdx:
        # Left out entirely when the licence has no SPDX identifier: the field
        # is validated against the list, and a wrong id is worse than none.
        data["license"] = spdx
    if pin.get("authors"):
        data["authors"] = pin["authors"]
    return data


def source_reference(pin):
    """The provenance every package ships, so a binary is traceable to a tag."""
    upstream = pin["upstream"]
    return "\n".join([
        f"upstream: {upstream['page']}",
        f"tag: {upstream['tag']}",
        f"commit: {upstream['commit']}",
        f"source archive: {upstream['url']}",
        f"source archive sha256: {upstream['sha256']}",
        *(line for data in pinned_data_files(pin) for line in (
            f"data file {data['to']}: {data['url']}",
            f"data file {data['to']} sha256: {data['sha256']}",
            f"data file {data['to']} origin: {data['origin']}",
        )),
        f"packaged by: https://github.com/apojomovsky/epic-tools",
        "",
    ])


def bundled_library_system_names(library):
    """The versioned and unversioned shared object names a library ships as.

    Copying the symlink as well as the target keeps a runtime lookup for
    ``libusb-1.0.so`` working as well as the ``.so.0`` a linked binary asks
    for by soname.
    """
    return (f"{library}.so", f"{library}.so.0")


def banner_check(pin):
    """The post-build probe: (argv, expected substring or None).

    A tool whose licence requires a visible notice (Microchip's PK2CMD clause
    1(b)) sets ``banner_must_match``, and the probe then fails the build rather
    than publishing a binary that does not carry it.
    """
    verify = pin["build"].get("verify") or {}
    args = verify.get("args")
    if not args:
        return None
    return list(args), verify.get("banner_must_match")


def main(argv=None):
    """Validate pin files. Exists so CI can gate a pin edit without building.

    One exit code for the caller: any bad pin fails the run, and every problem
    in every named pin is printed before exiting so one CI run reports the
    whole list rather than only the first file.
    """
    import argparse
    parser = argparse.ArgumentParser(prog="toolpin", description="Validate tool pins")
    parser.add_argument("--validate", metavar="PIN", action="append", default=[],
                        help="a pin file to validate; repeatable")
    parser.add_argument("paths", nargs="*", help="pin files (or directories holding one)")
    args = parser.parse_args(argv)

    targets = list(args.validate) + list(args.paths)
    if not targets:
        parser.error("give at least one pin file with --validate or as a path")

    failed = 0
    for target in targets:
        path = pathlib.Path(target)
        if path.is_dir():
            path = path / "pin.json"
        try:
            pin = load_pin(path)
        except PinError as err:
            print(f"FAIL {err}")
            failed += 1
            continue
        queue = patch_queue(path.parent)
        print(f"ok   {path}: {pin['package']} {pin['version']}, "
              f"systems={','.join(pin['systems'])}, {len(queue)} patch(es)")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
