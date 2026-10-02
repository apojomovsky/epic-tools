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
