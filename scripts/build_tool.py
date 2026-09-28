#!/usr/bin/env python3
"""Build one PlatformIO tool package from one pinned upstream tag.

Host side, the script only drives docker: nothing but docker is needed to
product a package, matching the ecosystem rule that no build toolchain is
installed on a host. Inside the container it fetches the pinned archive,
verifies its digest, applies the patch queue, builds, and assembles the
PlatformIO package directory.

Two hosts matter to this script and they are not the same thing: the docker
build host (`--system`, one of the PlatformIO system tokens) and the machine
running the build. A package built for `linux_x86_64` is built in a container,
so the building machine's glibc cannot leak into the artifact.

Usage:
  scripts/build_tool.py --pin tools/tool-minipro/pin.json --system linux_x86_64 --out dist
  scripts/build_tool.py --pin tools/tool-minipro/pin.json --system linux_x86_64 --out dist --in-container /work
"""

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import toolpin  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGE_TAG = "epic-tools-build:local"
PYTHON_IMAGE_TAG = "epic-tools-build-python:local"

# One image per build kind. A C tool needs a header-level-compatible base,
# which is why that image is pinned to the glibc floor epic-cc's toolchain
# carries; a pure-Python tool needs an interpreter new enough for its upstream
# (picpro wants 3.12) and has no compiled artifact, so it gets its own.
IMAGES = {
    "make": (IMAGE_TAG, REPO_ROOT / "docker" / "build" / "Dockerfile"),
    "python": (PYTHON_IMAGE_TAG, REPO_ROOT / "docker" / "build" / "python.Dockerfile"),
}

# The base image is pinned by digest, the same ubuntu:22.04 build epic-cc's
# toolchain uses. glibc 2.35 is the compatibility floor a released binary
# inherits, so the pin is a distribution decision, not housekeeping.
CONTAINER_WORK = "/work"
CONTAINER_REPO = "/repo"
CONSTRAINTS = "tools"


def log(message):
    print(f"build_tool: {message}", flush=True)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def drop_pycache(info):
    """Keep bytecode caches out of the package.

    `pip` writes them beside the vendored sources and they are pure build
    noise: they pin a CPython minor version into the artifact and are
    regenerated on first import.
    """
    if "__pycache__" in info.name or info.name.endswith(".pyc"):
        return None
    return info


def fetch(url, dest, expected_sha256):
    """Download `url`, then refuse it unless the digest matches the pin.

    The digest is checked before anything unpacks it: a pin is a statement
    about one exact upstream artifact, and a silently re-cut upstream tag is
    the failure this exists to catch.
    """
    log(f"fetch {url}")
    with urllib.request.urlopen(url) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)
    actual = sha256_of(dest)
    if actual != expected_sha256:
        raise SystemExit(
            f"digest mismatch for {url}\n  expected {expected_sha256}\n  actual   {actual}"
        )


def apply_queue(source_dir, patches):
    """Apply the patch queue in order, refusing to continue on a bad patch."""
    for patch in patches:
        log(f"apply {patch.name}")
        result = subprocess.run(
            ["git", "apply", "--verbose", "-p1", str(patch)],
            cwd=source_dir, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"patch {patch.name} did not apply:\n{result.stdout}{result.stderr}"
            )


def run_make(source_dir, pin, system):
    """Build a C tool, with the shared libraries resolved out of the package.

    `$$ORIGIN` survives into the binary's RUNPATH as the literal `$ORIGIN`
    because make expands the doubled dollar once. Relative RUNPATH is what
    lets the bundled library be found without LD_LIBRARY_PATH and without a
    host-wide install.
    """
    build = pin["build"]
    work_dir = source_dir / build.get("subdir", ".")
    # Single quotes survive make into the recipe's shell and hold the token
    # literal. Unquoted, make collapses the doubled dollar to one and the
    # recipe's shell then expands $ORIGIN away, leaving a RUNPATH of /lib that
    # matches nothing and silently binding the system libusb instead of ours.
    rpath = "-Wl,-rpath,'$$ORIGIN/lib' -Wl,--enable-new-dtags"
    # A command-line LDFLAGS replaces whatever the upstream Makefile set,
    # including the link library it configured, so a pin whose Makefile needs
    # one states it in build.ldflags rather than losing it to the override.
    ldflags = build.get("ldflags", "")
    make_args = list(build.get("make_args", []))
    command = ["make", *make_args, f"LDFLAGS={ldflags} {rpath}".strip()]
    if build.get("extra_make_vars"):
        command += [f"{k}={v}" for k, v in build["extra_make_vars"].items()]
    log(" ".join(command))
    result = subprocess.run(command, cwd=work_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"make failed:\n{result.stdout[-4000:]}{result.stderr[-4000:]}")
    built = work_dir / build["output"]
    if not built.exists():
        raise SystemExit(f"make reported success but {built} is missing")
    return built


def run_pip(package_dir, pin, source_dir):
    """Vendor a pure-Python tool and its dependencies with their licences.

    `pip install --target` is what carries each dependency's `*.dist-info`
    (METADATA plus its own LICENSE) into the package, which is how a vendored
    dependency ships its licence rather than merely its code. Installing from
    the extracted source rather than a version spec pins the vendored code to
    the same tag the pin names.
    """
    build = pin["build"]
    target = package_dir / build.get("vendor_dir", "vendor")
    target.mkdir(parents=True, exist_ok=True)
    requirement = build.get("requirement", ".")
    spec = str(source_dir) if requirement == "." else requirement
    command = [build.get("interpreter") or sys.executable, "-m", "pip", "install",
               "--no-compile", "--no-warn-script-location",
               "--target", str(target), spec]
    if build.get("constraints"):
        # Vendored dependencies are part of the artifact, so the set is pinned
        # by the tool directory rather than left to whatever PyPI serves on
        # build day.
        constraints = pathlib.Path(CONSTRAINTS) / build["constraints"]
        if not constraints.is_absolute():
            # Inside the container the repo root is mounted at CONTAINER_REPO.
            constraints = pathlib.Path(CONTAINER_REPO) / constraints
        if not constraints.exists():
            raise SystemExit(f"constraints file {constraints} does not exist")
        command += ["--constraint", str(constraints)]
    log(" ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"pip failed:\n{result.stdout[-4000:]}{result.stderr[-4000:]}")
    return target


def verify(pin, package_dir):
    """Probe the built tool, including any licence banner the pin demands."""
    probe = toolpin.banner_check(pin)
    if not probe:
        return
    argv, must_match = probe
    env = dict(os.environ)
    interpreter = pin["build"].get("interpreter") or sys.executable
    if pin["build"].get("home_dir"):
        env["MINIPRO_HOME"] = str(package_dir / pin["build"]["home_dir"])
    if pin["build"]["kind"] == "python":
        # The vendored tree is the import root, exactly as PlatformIO's own
        # interpreter will see it after unpacking the package.
        env["PYTHONPATH"] = str(package_dir / pin["build"].get("vendor_dir", "vendor"))
        # The pin names the entry point rather than assuming argv[0] resolves,
        # so an upstream rename is a one-line pin edit.
        command = [interpreter, str(package_dir / pin["build"]["entry_point"]),
                   *argv[1:]]
    else:
        command = [str(package_dir / argv[0].removeprefix("./")), *argv[1:]]
    log("verify " + " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    expected = pin["build"]["verify"].get("expect_exit")
    # A programmer tool with no hardware attached exits non-zero by design, so
    # the pin states the expectation rather than assuming zero.
    if expected is not None and result.returncode != expected:
        raise SystemExit(
            f"verify {command} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout[-2000:]}{result.stderr[-2000:]}"
        )
    if must_match:
        output = result.stdout + result.stderr
        if must_match not in output:
            raise SystemExit(
                f"licence banner check failed: {must_match!r} not in the output of "
                f"{command}; the packaged binary does not carry the notice the "
                f"licence requires"
            )
        log("licence banner present")


def stage(pin, package_dir, source_dir):
    """Put the runtime pieces in place before the probe runs.

    Data files and bundled libraries land first because the probe executes the
    built tool, and a programmer tool that cannot find its device database
    reports a failure that has nothing to do with the build.
    """
    for data in pin.get("data_files", []):
        source = source_dir / data["from"]
        if not source.exists():
            raise SystemExit(f"data file {data['from']} missing from the upstream tree")
        destination = package_dir / data["to"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    lib_dir = package_dir / "lib"
    for library in pin.get("bundled_libraries", []):
        lib_dir.mkdir(exist_ok=True)
        copied = 0
        for name in toolpin.bundled_library_system_names(library):
            for candidate in pathlib.Path("/usr/lib/x86_64-linux-gnu").glob(f"{name}*"):
                # The symlink and its versioned target both ship, so a lookup
                # by soname and by plain name resolve from inside the package.
                destination = lib_dir / candidate.name
                if not destination.exists():
                    if candidate.is_symlink():
                        destination.symlink_to(os.readlink(candidate))
                    else:
                        shutil.copy2(candidate, destination)
                    copied += 1
        if not copied:
            raise SystemExit(f"bundled library {library} not found in the build image")

    if pin.get("ship_source_tarball"):
        # GPL-3.0 minipro: the release carries the exact source it was built
        # from, so the binary's provenance is not a promise but a file.
        shutil.copy2(source_dir.parent / f"{pin['package']}.src.tar.gz",
                     package_dir / f"{pin['package']}.src.tar.gz")


def assemble(pin, system, package_dir, source_dir, archive_path, patches):
    """Write the licence, the source reference and the manifest, then tar.

    Every package ships its licence and a source reference (D-10), so both are
    written here rather than left to whoever builds by hand.
    """
    licence_file = pin["license"]["file"]
    licence_src = source_dir / licence_file
    if not licence_src.exists():
        raise SystemExit(f"licence file {licence_file} missing from the upstream tree")
    shutil.copy2(licence_src, package_dir / licence_file)
    (package_dir / "SOURCE.txt").write_text(toolpin.source_reference(pin))
    if pin.get("notice"):
        (package_dir / "NOTICE.txt").write_text(pin["notice"].rstrip() + "\n")
    for licence in pin.get("bundled_licences", []):
        # A dependency whose wheel omits its licence text would otherwise ship
        # code without the terms it requires alongside it.
        source = REPO_ROOT / "tools" / pin["package"] / "licences" / licence
        if not source.exists():
            raise SystemExit(f"declared licence file {licence} is missing from the pin directory")
        shutil.copy2(source, package_dir / licence)

    manifest = toolpin.manifest(pin, system)
    (package_dir / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if patches:
        (package_dir / "PATCHES.txt").write_text(
            "patches applied on top of the pinned tag:\n"
            + "".join(f"  {p.name}\n" for p in patches)
        )

    with tarfile.open(archive_path, "w:gz") as archive:
        for child in sorted(package_dir.iterdir()):
            archive.add(child, arcname=child.name, filter=drop_pycache)


def build_in_container(pin_path, system, out_dir):
    """The container half: everything after the host handed over the pin."""
    pin = toolpin.load_pin(pin_path)
    if system not in pin["systems"]:
        # A Linux ELF labelled windows_amd64 is worse than no package: the
        # registry would serve a binary no Windows machine can run.
        raise SystemExit(
            f"{pin['package']} declares {', '.join(pin['systems'])}; "
            f"{system} is not one of them. Declare it first or pick a host "
            f"the pin names."
        )
    pin_dir = pathlib.Path(pin_path).resolve().parent
    patches = toolpin.patch_queue(pin_dir)
    log(f"pin {pin['package']} {pin['version']} for {system}, "
        f"{len(patches)} patch(es) queued")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        downloaded = tmp / "upstream.tar.gz"
        fetch(pin["upstream"]["url"], downloaded, pin["upstream"]["sha256"])

        source_root = tmp / "src"
        source_root.mkdir()
        with tarfile.open(downloaded) as archive:
            # An explicit filter rather than the default: the default becomes
            # a filter in 3.14, and naming `data` now keeps the build quiet on
            # 3.12 while refusing any absolute path or link out of the tree.
            archive.extractall(source_root, filter="data")
        source_dir = source_root / pin["upstream"]["extract_dir"]
        if not source_dir.is_dir():
            raise SystemExit(
                f"the archive did not contain {pin['upstream']['extract_dir']}, "
                f"it held {[p.name for p in source_root.iterdir()]}"
            )

        if pin.get("ship_source_tarball"):
            # The exact source the binary was built from travels with it.
            shutil.copy2(downloaded, source_root / f"{pin['package']}.src.tar.gz")

        apply_queue(source_dir, patches)

        package_dir = tmp / "package"
        package_dir.mkdir()
        if pin["build"]["kind"] == "make":
            built = run_make(source_dir, pin, system)
            shutil.copy2(built, package_dir / built.name)
            (package_dir / built.name).chmod(0o755)
        else:
            vendor = run_pip(package_dir, pin, source_dir)
            log(f"vendored {len(list(vendor.iterdir()))} entries")

        # Layout before the probe: the tool has to find its data files and its
        # bundled libraries for the probe to mean anything.
        stage(pin, package_dir, source_dir)
        verify(pin, package_dir)

        out_dir = pathlib.Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        archive_path = out_dir / toolpin.archive_name(pin, system)
        assemble(pin, system, package_dir, source_dir, archive_path, patches)
        log(f"wrote {archive_path}")
        return archive_path


def image_for(pin):
    return IMAGES[pin["build"]["kind"]]


def docker_image_ready(tag):
    return subprocess.run(
        ["docker", "image", "inspect", tag], capture_output=True,
    ).returncode == 0


def build_image(tag, dockerfile):
    log(f"building {tag} (first run only)")
    result = subprocess.run(
        ["docker", "build", "-f", str(dockerfile), "-t", tag, str(REPO_ROOT)],
    )
    if result.returncode != 0:
        raise SystemExit(f"docker build failed for {dockerfile.name}")


def build_on_host(pin_path, system, out_dir):
    """The host half: no toolchain here, so the work happens in the container."""
    pin_path = pathlib.Path(pin_path).resolve()
    pin = toolpin.load_pin(pin_path)
    tag, dockerfile = image_for(pin)
    if not docker_image_ready(tag):
        build_image(tag, dockerfile)
    out_dir = pathlib.Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "docker", "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{REPO_ROOT}:{CONTAINER_REPO}",
        "-w", CONTAINER_REPO,
        tag,
        "python3", f"{CONTAINER_REPO}/scripts/build_tool.py",
        "--in-container", CONTAINER_WORK,
        "--pin", f"{CONTAINER_REPO}/{pin_path.relative_to(REPO_ROOT)}",
        "--system", system,
        "--out", f"{CONTAINER_REPO}/{out_dir.relative_to(REPO_ROOT)}",
    ]
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit(f"container build failed for {pin_path.name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build one PlatformIO tool package")
    parser.add_argument("--pin", required=True)
    parser.add_argument("--system", required=True, choices=sorted(toolpin.KNOWN_SYSTEMS))
    parser.add_argument("--out", required=True, help="output directory for the .tar.gz")
    parser.add_argument("--in-container", default=None, metavar="WORKDIR",
                        help="internal: run the build itself, not the docker driver")
    args = parser.parse_args(argv)

    if args.in_container:
        build_in_container(args.pin, args.system, args.out)
    else:
        build_on_host(args.pin, args.system, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
