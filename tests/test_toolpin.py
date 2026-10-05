"""Coverage for the tool pin rules and the packaging path.

No network, no docker, no upstream checkout: the pin rules are pure, and the
parts that touch the filesystem are exercised against small synthetic trees.
"""

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import toolpin  # noqa: E402
import build_tool  # noqa: E402

REAL_TOOLS = ("tool-minipro", "tool-pk2cmd", "tool-picpro")


def base_pin():
    return {
        "package": "tool-demo",
        "version": "1.2.3",
        "description": "a demo tool",
        "license": {"spdx": "MIT", "name": "MIT", "file": "LICENSE"},
        "upstream": {
            "url": "https://example.invalid/demo-1.2.3.tar.gz",
            "page": "https://example.invalid/demo",
            "tag": "v1.2.3",
            "commit": "0" * 40,
            "sha256": "a" * 64,
            "extract_dir": "demo-1.2.3",
        },
        "build": {"kind": "make", "output": "demo"},
        "systems": ["linux_x86_64"],
    }


class ValidateTest(unittest.TestCase):
    def test_a_complete_pin_has_no_problems(self):
        self.assertEqual(toolpin.validate(base_pin()), [])

    def test_each_missing_required_field_is_named(self):
        for field in toolpin.REQUIRED:
            pin = base_pin()
            del pin[field]
            problems = toolpin.validate(pin)
            self.assertTrue(any(field in p for p in problems), f"{field}: {problems}")

    def test_a_short_digest_is_rejected(self):
        pin = base_pin()
        pin["upstream"]["sha256"] = "abc123"
        self.assertTrue(any("sha256" in p for p in toolpin.validate(pin)))

    def test_an_unknown_system_is_rejected(self):
        pin = base_pin()
        pin["systems"] = ["plan9"]
        self.assertTrue(any("plan9" in p for p in toolpin.validate(pin)))

    def test_a_licence_with_neither_id_nor_name_is_rejected(self):
        pin = base_pin()
        pin["license"] = {"file": "LICENSE"}
        self.assertTrue(any("spdx id or a name" in p for p in toolpin.validate(pin)))

    def test_a_make_build_must_name_its_output(self):
        pin = base_pin()
        del pin["build"]["output"]
        self.assertTrue(any("build.output" in p for p in toolpin.validate(pin)))

    def test_a_python_build_needs_no_output_binary(self):
        pin = base_pin()
        pin["build"] = {"kind": "python", "requirement": "."}
        self.assertEqual(toolpin.validate(pin), [])

    def test_an_unknown_build_kind_is_rejected(self):
        pin = base_pin()
        pin["build"] = {"kind": "cmake", "output": "demo"}
        self.assertTrue(any("build.kind" in p for p in toolpin.validate(pin)))

    def test_a_data_file_from_the_upstream_tree_is_valid(self):
        pin = base_pin()
        pin["data_files"] = [{"from": "db.xml", "to": "share/db.xml"}]
        self.assertEqual(toolpin.validate(pin), [])

    def test_a_data_file_pinned_by_url_needs_a_digest(self):
        pin = base_pin()
        pin["data_files"] = [{"url": "https://example.invalid/db", "to": "db",
                              "origin": "vendor db 2.0"}]
        self.assertTrue(any("sha256" in p for p in toolpin.validate(pin)))
        pin["data_files"][0]["sha256"] = "b" * 64
        self.assertEqual(toolpin.validate(pin), [])

    def test_a_data_file_pinned_by_url_needs_an_origin(self):
        pin = base_pin()
        pin["data_files"] = [{"url": "https://example.invalid/db", "to": "db",
                              "sha256": "b" * 64}]
        self.assertTrue(any("origin" in p for p in toolpin.validate(pin)))

    def test_two_data_files_cannot_share_a_destination(self):
        pin = base_pin()
        pin["data_files"] = [
            {"from": "db", "to": "share/db"},
            {"url": "https://example.invalid/db", "sha256": "b" * 64,
             "origin": "vendor db 2.0", "to": "share//db"},
        ]
        self.assertTrue(any("repeats destination" in p for p in toolpin.validate(pin)))

    def test_a_data_file_names_exactly_one_source(self):
        for data in ({"to": "db"},
                     {"from": "db", "url": "https://example.invalid/db",
                      "sha256": "b" * 64, "origin": "vendor db 2.0", "to": "db"}):
            pin = base_pin()
            pin["data_files"] = [data]
            self.assertTrue(any("exactly one" in p for p in toolpin.validate(pin)),
                            data)

    def test_a_data_file_without_a_destination_is_rejected(self):
        pin = base_pin()
        pin["data_files"] = [{"from": "db"}]
        self.assertTrue(any("'to'" in p for p in toolpin.validate(pin)))

    def test_a_non_object_pin_is_rejected_rather_than_crashing(self):
        self.assertEqual(toolpin.validate(["not", "an", "object"]),
                         ["pin must be a JSON object"])


class LoadPinTest(unittest.TestCase):
    def test_a_malformed_file_names_the_path_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "pin.json"
            path.write_text("{not json")
            with self.assertRaises(toolpin.PinError) as caught:
                toolpin.load_pin(path)
            self.assertIn("not valid JSON", str(caught.exception))

    def test_a_missing_file_names_the_path(self):
        with self.assertRaises(toolpin.PinError) as caught:
            toolpin.load_pin("/nonexistent/pin.json")
        self.assertIn("cannot read", str(caught.exception))

    def test_a_pin_with_a_problem_reports_it_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "pin.json"
            pin = base_pin()
            pin["systems"] = []
            path.write_text(json.dumps(pin))
            with self.assertRaises(toolpin.PinError):
                toolpin.load_pin(path)


class ShippedPinsTest(unittest.TestCase):
    """The three real pins are the repo's contract with its own CI."""

    def test_every_shipped_pin_validates(self):
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            self.assertEqual(pin["package"], name)

    def test_every_shipped_pin_names_a_licence_file_it_ships(self):
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            self.assertTrue(pin["license"]["file"], name)

    def test_every_shipped_pin_routes_registry_links_here_not_upstream(self):
        # Upstream never sees this build, so its tracker must not receive
        # packaging reports; the manifest carries this repo instead, and the
        # description says plainly that the package is unofficial.
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            data = toolpin.manifest(pin, pin["systems"][0])
            self.assertIn("github.com/apojomovsky/epic-tools",
                          data["homepage"], name)
            self.assertIn("github.com/apojomovsky/epic-tools",
                          data["repository"]["url"], name)
            self.assertTrue(pin["description"].startswith("Unofficial epic8 package of"),
                            name)

    def test_minipro_ships_its_source_tarball(self):
        pin = toolpin.load_pin(ROOT / "tools" / "tool-minipro" / "pin.json")
        self.assertTrue(pin["ship_source_tarball"])

    def test_pk2cmd_carries_the_microchip_notice_and_a_patch_for_it(self):
        pin = toolpin.load_pin(ROOT / "tools" / "tool-pk2cmd" / "pin.json")
        self.assertIn("modified by the epic8 project", pin["notice"])
        queue = toolpin.patch_queue(ROOT / "tools" / "tool-pk2cmd")
        self.assertTrue(queue, "the placeholder notice needs a patch to fill it")
        body = queue[0].read_text()
        self.assertIn("INSERT YOUR NAME", body)
        self.assertIn("modified by the epic8 project", body)

    def test_pk2cmd_checks_its_banner_and_minipro_does_not(self):
        pk2 = toolpin.load_pin(ROOT / "tools" / "tool-pk2cmd" / "pin.json")
        mini = toolpin.load_pin(ROOT / "tools" / "tool-minipro" / "pin.json")
        pk2_argv, pk2_banner = toolpin.banner_check(pk2)
        # pk2cmd's licence requires a visible notice, so its probe checks one;
        # GPL minipro has nothing to verify beyond exit status.
        self.assertEqual(pk2_argv, ["./pk2cmd", "-?l"])
        self.assertIn("modified by the epic8 project", pk2_banner)
        mini_argv, mini_banner = toolpin.banner_check(mini)
        self.assertEqual(mini_argv, ["./minipro", "--version"])
        self.assertIsNone(mini_banner)

    def test_pk2cmd_ships_microchips_device_file_not_upstreams(self):
        # jaka-fi's PK2DeviceFile.dat is under the PICkitPlus claim, so the
        # device file must come from its own pin, never the upstream tree.
        pin = toolpin.load_pin(ROOT / "tools" / "tool-pk2cmd" / "pin.json")
        shipped = [d for d in pin["data_files"] if d["to"] == "PK2DeviceFile.dat"]
        self.assertEqual(len(shipped), 1)
        self.assertNotIn("from", shipped[0])
        self.assertIn(shipped[0], toolpin.pinned_data_files(pin))
        self.assertIn("1.62.14", shipped[0]["origin"])

    def test_bundled_libraries_are_declared_as_shared_object_names(self):
        # A shared object is what the build driver globs and copies, so a pin
        # naming a library some other way ships nothing.
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            for library in pin.get("bundled_libraries", []):
                self.assertRegex(library, r"^lib\w+(-[\d.]+)?$")
                self.assertTrue(toolpin.bundled_library_system_names(library),
                                f"{name}: {library}")

    def test_every_shipped_pin_declares_both_hosts(self):
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            self.assertEqual(pin["systems"],
                             ["linux_x86_64", "windows_amd64"], name)

    def test_windows_c_binaries_ship_no_bundled_library(self):
        # The Windows backends use system libraries (WinUSB, HID) with static
        # runtimes, so a Windows package carries no lib/ directory at all.
        for name in ("tool-minipro", "tool-pk2cmd"):
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            effective = toolpin.effective_build(pin, "windows_amd64")
            self.assertTrue(effective["output"].endswith(".exe"), name)
            self.assertEqual(effective.get("bundled_libraries",
                             pin.get("bundled_libraries")), [], name)

    def test_picpro_builds_one_tree_for_both_hosts(self):
        pin = toolpin.load_pin(ROOT / "tools" / "tool-picpro" / "pin.json")
        self.assertNotIn("per_system", pin["build"])
        self.assertEqual(toolpin.effective_build(pin, "windows_amd64"),
                         toolpin.effective_build(pin, "linux_x86_64"))


class PatchQueueTest(unittest.TestCase):
    def test_no_patch_directory_means_an_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(toolpin.patch_queue(tmp), [])

    def test_an_empty_patch_directory_means_an_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "patches").mkdir()
            self.assertEqual(toolpin.patch_queue(tmp), [])

    def test_patches_apply_in_filename_order_not_directory_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch_dir = pathlib.Path(tmp) / "patches"
            patch_dir.mkdir()
            for name in ("0010-later.patch", "0002-earlier.patch", "0001-first.diff"):
                (patch_dir / name).write_text("x")
            names = [p.name for p in toolpin.patch_queue(tmp)]
            self.assertEqual(names, ["0001-first.diff", "0002-earlier.patch",
                                     "0010-later.patch"])

    def test_a_non_patch_file_is_not_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch_dir = pathlib.Path(tmp) / "patches"
            patch_dir.mkdir()
            (patch_dir / "README.md").write_text("notes")
            (patch_dir / "0001-fix.patch").write_text("x")
            self.assertEqual([p.name for p in toolpin.patch_queue(tmp)],
                             ["0001-fix.patch"])


class ManifestTest(unittest.TestCase):
    def test_the_manifest_names_the_package_and_version(self):
        pin = base_pin()
        data = toolpin.manifest(pin, "linux_x86_64")
        self.assertEqual(data["name"], "tool-demo")
        self.assertEqual(data["version"], "1.2.3")

    def test_windows_maps_to_every_spelling_the_registry_uses(self):
        pin = base_pin()
        pin["systems"] = ["windows_amd64"]
        data = toolpin.manifest(pin, "windows_amd64")
        self.assertIn("windows_amd64", data["system"])
        self.assertIn("windows_x86_64", data["system"])

    def test_a_licence_without_an_spdx_id_omits_the_manifest_field(self):
        # PlatformIO validates the field against the SPDX list, so carrying a
        # made-up id is worse than carrying none.
        pin = base_pin()
        pin["license"] = {"name": "Microchip PK2CMD Software License",
                          "file": "license.txt"}
        data = toolpin.manifest(pin, "linux_x86_64")
        self.assertNotIn("license", data)

    def test_an_spdx_id_carries_into_the_manifest(self):
        data = toolpin.manifest(base_pin(), "linux_x86_64")
        self.assertEqual(data["license"], "MIT")

    def test_a_pin_homepage_overrides_the_upstream_page(self):
        pin = base_pin()
        pin["homepage"] = "https://example.invalid/tools"
        data = toolpin.manifest(pin, "linux_x86_64")
        self.assertEqual(data["homepage"], "https://example.invalid/tools")

    def test_without_a_pin_homepage_the_upstream_page_is_kept(self):
        data = toolpin.manifest(base_pin(), "linux_x86_64")
        self.assertEqual(data["homepage"], "https://example.invalid/demo")


class ArchiveNameTest(unittest.TestCase):
    def test_the_archive_name_carries_package_system_and_version(self):
        name = toolpin.archive_name(base_pin(), "linux_x86_64")
        self.assertEqual(name, "tool-demo-linux_x86_64-1.2.3.tar.gz")


class VersionSchemeTest(unittest.TestCase):
    """The package version names its upstream, bare first, +pioN after that."""

    def test_a_bare_upstream_version_validates(self):
        pin = base_pin()
        pin["version"] = "1.2.3"
        self.assertEqual(toolpin.validate(pin), [])

    def test_a_packaging_revision_validates(self):
        pin = base_pin()
        pin["version"] = "1.2.3+pio1"
        self.assertEqual(toolpin.validate(pin), [])

    def test_shapes_outside_the_scheme_are_rejected(self):
        for version in ("1.2", "1.2.3.4", "v1.2.3", "1.02.3",
                        "1.2.3-pio.1", "1.2.3+pio0", "1.2.3+build",
                        "1.2.3+pio", ""):
            pin = base_pin()
            pin["version"] = version
            self.assertTrue(toolpin.validate(pin), version)

    def test_a_tag_with_a_v_prefix_and_zeros_folds_to_the_version(self):
        self.assertEqual(toolpin.upstream_version("v1.27.01"), "1.27.1")

    def test_a_plain_tag_folds_to_itself(self):
        self.assertEqual(toolpin.upstream_version("0.7.4"), "0.7.4")

    def test_a_tag_with_no_plain_version_folds_to_nothing(self):
        self.assertIsNone(toolpin.upstream_version("nightly"))

    def test_a_version_from_another_upstream_is_rejected(self):
        pin = base_pin()
        pin["version"] = "1.2.4"
        problems = toolpin.validate(pin)
        self.assertTrue(any("upstream.tag" in p for p in problems))

    def test_a_packaging_revision_of_the_pinned_upstream_validates(self):
        pin = base_pin()
        pin["version"] = "1.2.3+pio2"
        self.assertEqual(toolpin.validate(pin), [])

    def test_a_packaging_revision_of_another_upstream_is_rejected(self):
        pin = base_pin()
        pin["upstream"]["tag"] = "v1.2.4"
        pin["version"] = "1.2.3+pio1"
        self.assertTrue(toolpin.validate(pin))

    def test_every_shipped_pin_names_its_own_upstream(self):
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            core, _ = toolpin.split_package_version(pin["version"])
            self.assertEqual(core, toolpin.upstream_version(pin["upstream"]["tag"]), name)

    def test_the_manifest_and_archive_carry_the_full_revision(self):
        pin = base_pin()
        pin["version"] = "1.2.3+pio1"
        self.assertEqual(toolpin.manifest(pin, "linux_x86_64")["version"], "1.2.3+pio1")
        self.assertEqual(toolpin.archive_name(pin, "linux_x86_64"),
                         "tool-demo-linux_x86_64-1.2.3+pio1.tar.gz")


class SourceReferenceTest(unittest.TestCase):
    def test_the_reference_names_the_tag_commit_and_digest(self):
        text = toolpin.source_reference(base_pin())
        for fact in ("v1.2.3", "0" * 40, "a" * 64,
                     "https://example.invalid/demo-1.2.3.tar.gz"):
            self.assertIn(fact, text)

    def test_a_pinned_data_file_is_traceable_from_the_reference(self):
        pin = base_pin()
        pin["data_files"] = [
            {"from": "local.xml", "to": "local.xml"},
            {"url": "https://example.invalid/db", "sha256": "b" * 64,
             "to": "db", "origin": "vendor db 2.0"},
        ]
        text = toolpin.source_reference(pin)
        for fact in ("https://example.invalid/db", "b" * 64, "vendor db 2.0"):
            self.assertIn(fact, text)
        self.assertNotIn("local.xml", text)


class BundledLibraryTest(unittest.TestCase):
    def test_a_library_ships_under_both_its_soname_and_plain_name(self):
        names = toolpin.bundled_library_system_names("libusb-1.0")
        self.assertIn("libusb-1.0.so", names)
        self.assertIn("libusb-1.0.so.0", names)


if __name__ == "__main__":
    unittest.main()


class SystemDeclarationTest(unittest.TestCase):
    """A host a pin does not declare must be refused, not mislabelled."""

    def test_shipped_pins_declare_the_host_their_archive_name_uses(self):
        for name in REAL_TOOLS:
            pin = toolpin.load_pin(ROOT / "tools" / name / "pin.json")
            self.assertTrue(pin["systems"], name)
            self.assertIn("linux_x86_64", toolpin.systems_of(pin, pin["systems"][0]))

    def test_the_archive_name_carries_the_host_that_was_asked_for(self):
        pin = base_pin()
        self.assertEqual(
            toolpin.archive_name(pin, "windows_amd64"),
            "tool-demo-windows_amd64-1.2.3.tar.gz",
        )

    def test_windows_mapping_covers_both_registry_spellings(self):
        pin = base_pin()
        pin["systems"] = ["windows_amd64"]
        self.assertEqual(toolpin.systems_of(pin, "windows_amd64"),
                         ["windows_amd64", "windows_x86_64"])


class EffectiveBuildTest(unittest.TestCase):
    def test_without_an_entry_the_base_build_is_returned_whole(self):
        pin = base_pin()
        self.assertEqual(toolpin.effective_build(pin, "linux_x86_64"),
                         pin["build"])

    def test_an_entry_replaces_only_the_keys_it_names(self):
        pin = base_pin()
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"windows_amd64": {"output": "demo.exe"}}
        effective = toolpin.effective_build(pin, "windows_amd64")
        self.assertEqual(effective["output"], "demo.exe")
        self.assertNotIn("per_system", effective)
        self.assertEqual(toolpin.effective_build(pin, "linux_x86_64")["output"],
                         "demo")

    def test_make_vars_merge_while_other_keys_replace(self):
        pin = base_pin()
        pin["build"]["extra_make_vars"] = {"BASE": "1"}
        pin["build"]["per_system"] = {"windows_amd64": {
            "extra_make_vars": {"BASE": "2", "CC": "x"}, "ldflags": "-lhid"}}
        effective = toolpin.effective_build(pin, "windows_amd64")
        self.assertEqual(effective["extra_make_vars"], {"BASE": "2", "CC": "x"})
        self.assertEqual(effective["ldflags"], "-lhid")


class PerSystemValidateTest(unittest.TestCase):
    def windows_pin(self):
        pin = base_pin()
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"windows_amd64": {
            "output": "demo.exe",
            "verify": {"args": ["./demo.exe", "--version"]},
        }}
        return pin

    def test_a_valid_windows_entry_has_no_problems(self):
        self.assertEqual(toolpin.validate(self.windows_pin()), [])

    def test_an_unknown_host_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"] = {"plan9": {}}
        self.assertTrue(any("plan9" in p for p in toolpin.validate(pin)))

    def test_an_undeclared_host_is_rejected(self):
        pin = base_pin()
        pin["build"]["per_system"] = {"windows_amd64": {"output": "demo.exe"}}
        problems = toolpin.validate(pin)
        self.assertTrue(any("does not declare" in p for p in problems))

    def test_an_unknown_build_key_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["bogus"] = 1
        problems = toolpin.validate(pin)
        self.assertTrue(any("bogus" in p for p in problems))

    def test_a_windows_make_output_without_exe_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["output"] = "demo"
        problems = toolpin.validate(pin)
        self.assertTrue(any(".exe" in p for p in problems))

    def test_a_windows_verify_with_an_exit_expectation_is_rejected(self):
        # A cross-built PE cannot execute on the Linux build host, so an
        # exit expectation could never be honored there.
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["verify"]["expect_exit"] = 0
        problems = toolpin.validate(pin)
        self.assertTrue(any("exit code" in p for p in problems))

    def test_a_windows_verify_with_an_empty_string_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["verify"] = {
            "strings_must_match": [""]}
        problems = toolpin.validate(pin)
        self.assertTrue(any("empty string" in p for p in problems))

    def test_a_non_object_make_vars_entry_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["extra_make_vars"] = "CC=x"
        problems = toolpin.validate(pin)
        self.assertTrue(any("must be an object" in p for p in problems))

    def test_a_non_list_strings_entry_is_rejected(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["verify"] = {
            "strings_must_match": "demo banner"}
        problems = toolpin.validate(pin)
        self.assertTrue(any("non-empty strings" in p for p in problems))

    def test_a_malformed_entry_loads_as_a_pin_error_not_a_crash(self):
        pin = self.windows_pin()
        pin["build"]["per_system"]["windows_amd64"]["extra_make_vars"] = "CC=x"
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "pin.json"
            path.write_text(json.dumps(pin))
            with self.assertRaises(toolpin.PinError):
                toolpin.load_pin(path)


class PeMachineTest(unittest.TestCase):
    """The cross-build probe reads the PE header itself, no `file` tool."""

    def image_with_machine(self, machine):
        header = b"MZ" + b"\0" * 58 + (64).to_bytes(4, "little")
        return header + b"PE\0\0" + machine.to_bytes(2, "little")

    def test_an_amd64_image_reports_its_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "demo.exe"
            binary.write_bytes(self.image_with_machine(0x8664))
            self.assertEqual(build_tool.pe_machine(binary), 0x8664)

    def test_a_non_pe_file_reports_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "demo"
            binary.write_bytes(b"\x7fELF" + b"\0" * 60)
            self.assertIsNone(build_tool.pe_machine(binary))

    def test_a_truncated_header_reports_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / "demo.exe"
            binary.write_bytes(b"MZ" + b"\0" * 10)
            self.assertIsNone(build_tool.pe_machine(binary))


class StripHostObjectsTest(unittest.TestCase):
    def test_only_shared_objects_leave_the_vendor_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            vendor = pathlib.Path(tmp)
            (vendor / "fast.so").write_bytes(b"x")
            (vendor / "sub").mkdir()
            (vendor / "sub" / "deep.so").write_bytes(b"x")
            (vendor / "slow.py").write_text("x")
            self.assertEqual(build_tool.strip_host_objects(vendor), 2)
            self.assertFalse((vendor / "fast.so").exists())
            self.assertTrue((vendor / "slow.py").exists())


class VerifyTest(unittest.TestCase):
    """The probe executes staged Linux binaries and inspects Windows ones."""

    def staged_script(self, package, name="demo"):
        prog = package / name
        prog.write_text("#!/bin/sh\necho demo banner\n")
        prog.chmod(0o755)
        return prog

    def test_the_linux_probe_executes_the_staged_binary(self):
        pin = base_pin()
        pin["build"]["verify"] = {"args": ["./demo"],
                                  "expect_exit": 0,
                                  "banner_must_match": "demo banner"}
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            self.staged_script(package)
            build_tool.verify(pin, package, "linux_x86_64")

    def test_the_linux_probe_refuses_a_binary_missing_its_banner(self):
        pin = base_pin()
        pin["build"]["verify"] = {"args": ["./demo"],
                                  "banner_must_match": "demo banner"}
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            prog = package / "demo"
            prog.write_text("#!/bin/sh\necho something else\n")
            prog.chmod(0o755)
            with self.assertRaises(SystemExit):
                build_tool.verify(pin, package, "linux_x86_64")

    def test_the_windows_probe_checks_kind_and_strings(self):
        pin = base_pin()
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"windows_amd64": {
            "output": "demo.exe",
            "verify": {"args": ["./demo.exe"],
                       "strings_must_match": ["demo banner"]}}}
        header = b"MZ" + b"\0" * 58 + (64).to_bytes(4, "little")
        image = header + b"PE\0\0" + (0x8664).to_bytes(2, "little")
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            (package / "demo.exe").write_bytes(image + b"demo banner")
            build_tool.verify(pin, package, "windows_amd64")

    def test_the_windows_probe_refuses_a_non_pe_binary(self):
        pin = base_pin()
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"windows_amd64": {"output": "demo.exe"}}
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            (package / "demo.exe").write_bytes(b"\x7fELF" + b"\0" * 60)
            with self.assertRaises(SystemExit):
                build_tool.verify(pin, package, "windows_amd64")

    def test_the_linux_probe_honors_a_per_system_verify_entry(self):
        pin = base_pin()
        pin["build"]["verify"] = {"args": ["./demo"],
                                  "banner_must_match": "base banner"}
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"linux_x86_64": {
            "verify": {"args": ["./demo"],
                       "banner_must_match": "demo banner"}}}
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            self.staged_script(package)
            build_tool.verify(pin, package, "linux_x86_64")

    def test_the_windows_probe_checks_the_banner_text_too(self):
        pin = base_pin()
        pin["systems"] = ["linux_x86_64", "windows_amd64"]
        pin["build"]["per_system"] = {"windows_amd64": {
            "output": "demo.exe",
            "verify": {"args": ["./demo.exe"],
                       "banner_must_match": "demo banner"}}}
        header = b"MZ" + b"\0" * 58 + (64).to_bytes(4, "little")
        image = header + b"PE\0\0" + (0x8664).to_bytes(2, "little")
        with tempfile.TemporaryDirectory() as tmp:
            package = pathlib.Path(tmp)
            (package / "demo.exe").write_bytes(image + b"something else")
            with self.assertRaises(SystemExit):
                build_tool.verify(pin, package, "windows_amd64")
            (package / "demo.exe").write_bytes(image + b"demo banner")
            build_tool.verify(pin, package, "windows_amd64")
