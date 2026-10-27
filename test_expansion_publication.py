"""Static publication checks use tiny synthetic outcomes, never study retuning."""
from __future__ import annotations

import contextlib
import copy
import csv
import gzip
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import expansion_publication as publication
import expansion_study as study
from audit_expansion_research import audit
from test_expansion_study import FakeGame


class ExpansionPathGateTests(unittest.TestCase):
    def setUp(self):
        scratch=publication.ROOT/".ai-work"/"runs"/"20261018-expansion"
        scratch.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix="publication-path-test-",dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()

    def test_lexically_contained_parent_traversal_cannot_read_outside_source_root(self):
        outside=self.base/"outside.txt"
        outside.write_bytes(b"outside source root")
        with self.assertRaises(publication.ExpansionPublicationError):
            publication.regular(self.repo/".."/outside.name,base=self.repo)
        inside=self.repo/"inside.txt"
        inside.write_bytes(b"inside source root")
        self.assertEqual(publication.regular(inside,base=self.repo),b"inside source root")

    def test_original_link_components_are_rejected_even_when_resolved_target_is_inside(self):
        folder=self.repo/"inside"
        folder.mkdir()
        (folder/"data.txt").write_bytes(b"inside source root")
        link=self.repo/"linked"
        link.symlink_to(folder,target_is_directory=True)
        with self.assertRaises(publication.ExpansionPublicationError):
            publication.regular(link/"data.txt",base=self.repo)

    def test_custom_study_cannot_escape_source_root_before_scientific_validation(self):
        (self.base/"outside-study").mkdir()
        with patch.object(publication,"_validate_study",side_effect=AssertionError("validation must not run")) as validator:
            with self.assertRaises(publication.ExpansionPublicationError):
                publication.build_expansion_publication(self.repo,self.repo/"dist"/"evidence",
                    study_dir=self.repo/".."/"outside-study")
            validator.assert_not_called()


class ExpansionPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = publication.ROOT / ".ai-work" / "runs" / "20261018-expansion"
        scratch.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="publication-test-", dir=scratch)
        cls.base = Path(cls.temporary.name)
        cls.source = cls.base / "source"
        cls.source.mkdir()
        for name in study.SOURCE_FILES:
            (cls.source / name).write_text("raise RuntimeError('Bundled code must never execute')\n")
        for name in publication.DOCS:
            path = cls.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Synthetic publication fixture\n")
        cls.study_dir = cls.source / publication.STUDY_PATH
        configs = {p: {"name": p} for p in study.POLICIES}
        with patch.object(study, "ROOT", cls.source), patch.object(study, "_configuration_catalogue", return_value=configs), \
                patch.dict(sys.modules, {"expansion_simulator": SimpleNamespace(ExpansionGame=FakeGame)}), contextlib.redirect_stdout(io.StringIO()):
            study.freeze_plan(cls.study_dir, screen_blocks=2, confirmation_blocks=2, counter_search_blocks=2, counter_blocks=2)
            cls.findings = study.run_study(cls.study_dir, workers=1)
            cls.replay = audit(cls.study_dir, source_root=cls.source, game_class=FakeGame)
        (cls.study_dir / "replay-audit.json").write_bytes(publication.canonical(cls.replay))
        cls.evidence = cls.source / "dist" / "evidence"
        with patch.object(publication, "_validate_study", return_value=(cls.findings,cls.replay)):
            cls.payload = publication.build_expansion_publication(cls.source, cls.evidence)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="static-", dir=self.base)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / "dist" / "evidence"
        shutil.copytree(self.evidence_source, self.evidence)
        self.anchor = {"expansion_study": copy.deepcopy(self.payload["anchor"])}
        self.embedded = {"expansion":copy.deepcopy(self.payload["expansion"]), "expansion_configs":copy.deepcopy(self.payload["expansion_configs"])}
        self.publication = copy.deepcopy(self.payload["publication"])

    @property
    def evidence_source(self):
        return type(self).evidence

    def verify(self):
        return publication.verify_expansion_bundle(self.root,self.evidence,self.embedded,self.anchor,self.publication)

    def saved(self):
        return publication._archive(self.evidence,self.anchor["expansion_study"])

    def repack(self,saved,*,member_override=None,duplicate=None):
        inventory = {name:{"size":len(raw),"sha256":publication.sha(raw)} for name,raw in sorted(saved.items())}
        output=io.BytesIO()
        with gzip.GzipFile(filename="",fileobj=output,mode="wb",mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode="w",format=tarfile.USTAR_FORMAT) as archive:
                for name,raw in sorted(saved.items()):
                    info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644
                    if member_override and name==member_override:
                        info.type=tarfile.SYMTYPE;info.linkname="outside";info.size=0
                    archive.addfile(info,io.BytesIO(raw) if info.isfile() else None)
                    if name==duplicate:archive.addfile(info,io.BytesIO(raw))
        archive=output.getvalue();manifest=publication.canonical(inventory)
        (self.evidence/"expansion-evidence.tar.gz").write_bytes(archive)
        (self.evidence/"expansion-bundle-manifest.json").write_bytes(manifest)
        self.anchor["expansion_study"].update(bundle_sha256=publication.sha(archive),bundle_manifest_sha256=publication.sha(manifest))

    def test_extracted_site_verifies_without_importing_any_bundled_module(self):
        blocked={name:None for name in ("expansion_simulator","expansion_study","expansion_statistics","audit_expansion_research")}
        with patch.dict(sys.modules,blocked):
            receipt=self.verify()
        self.assertEqual(receipt["total_games"],16920)
        self.assertEqual(receipt["total_replayed_games"],16920)
        self.assertGreater(receipt["files"],2800)

    def test_isolated_python_can_load_trusted_helper_for_an_extracted_site(self):
        inputs=self.root/"inputs.json"
        inputs.write_bytes(publication.canonical({"embedded":self.embedded,"anchor":self.anchor,"publication":self.publication}))
        script=("import importlib.util,json,pathlib,sys; "
            "spec=importlib.util.spec_from_file_location('trusted_publication',sys.argv[1]); "
            "helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper); "
            "root=pathlib.Path(sys.argv[2]); data=json.loads((root/'inputs.json').read_text()); "
            "result=helper.verify_expansion_bundle(root,root/'dist'/'evidence',data['embedded'],data['anchor'],data['publication']); "
            "assert result['total_games']==16920")
        result=subprocess.run([sys.executable,"-I","-B","-c",script,str(publication.ROOT/"expansion_publication.py"),str(self.root)],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_deterministic_bundle_and_complete_public_outputs(self):
        before={name:(self.evidence_source/name).read_bytes() for name in publication.PUBLIC_FILES}
        second=self.source/"second"/"evidence"
        with patch.object(publication,"_validate_study",return_value=(self.findings,self.replay)):
            payload=publication.build_expansion_publication(self.source,second)
        self.assertEqual(payload,self.payload)
        self.assertEqual({p.name for p in second.iterdir()},set(publication.PUBLIC_FILES))
        self.assertEqual({name:(second/name).read_bytes() for name in publication.PUBLIC_FILES},before)
        shutil.rmtree(second.parent)

    def test_external_approval_is_required_and_cannot_be_replaced_by_self_hashes(self):
        self.anchor={}
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()
        self.anchor={"expansion_study":copy.deepcopy(self.payload["anchor"])}
        path=self.evidence/"expansion-evidence.tar.gz"
        path.write_bytes(path.read_bytes()+b"changed")
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_unsafe_archive_path_rejected_with_updated_inventory_hash(self):
        saved=self.saved();saved["../outside"] = b"unsafe"
        self.repack(saved)
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_duplicate_archive_member_rejected(self):
        saved=self.saved()
        self.repack(saved,duplicate=next(iter(saved)))
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_archive_links_rejected(self):
        saved=self.saved()
        self.repack(saved,member_override=next(iter(saved)))
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_unplanned_archive_member_rejected_even_when_hashes_match(self):
        saved=self.saved();saved["docs/unreviewed.md"] = b"extra"
        self.repack(saved)
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_changed_download_and_embedded_policy_settings_rejected(self):
        path=self.evidence/"expansion-findings.json"
        original=path.read_bytes();path.write_bytes(original+b" ")
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()
        path.write_bytes(original)
        self.embedded["expansion_configs"]["honest"]["name"]="altered"
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_wrong_seed_rejected_after_rehashing_raw_diagnostic_and_stage_manifest(self):
        saved=self.saved()
        prefix=publication.STUDY_PATH+"/screening/"
        rawname=next(name for name in sorted(saved) if name.startswith(prefix) and name.endswith(".csv.gz"))
        reader=csv.DictReader(io.StringIO(gzip.decompress(saved[rawname]).decode()))
        rows=list(reader);rows[0]["seed"]="0"
        text=io.StringIO(newline="");writer=csv.DictWriter(text,fieldnames=publication.RAW_COLUMNS)
        writer.writeheader();writer.writerows(rows)
        saved[rawname]=gzip.compress(text.getvalue().encode(),mtime=0)
        diagname=str(Path(rawname).with_suffix(".diagnostics.json"))
        diagnostic=publication.parse(saved[diagname]);diagnostic["raw_sha256"]=publication.sha(saved[rawname])
        saved[diagname]=publication.canonical(diagnostic)
        manifestname=prefix+"manifest.json";manifest=publication.parse(saved[manifestname])
        for name in (rawname,diagname):manifest["files"][name[len(prefix):]]=publication.sha(saved[name])
        saved[manifestname]=publication.canonical(manifest)
        self.repack(saved)
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_changed_statistical_claim_rejected_even_with_updated_findings_approval(self):
        saved=self.saved();name=publication.STUDY_PATH+"/findings.json"
        findings=publication.parse(saved[name]);findings["confirmation_pairs"][0]["difference"] += .01
        saved[name]=publication.canonical(findings)
        self.embedded["expansion"]=findings
        (self.evidence/"expansion-findings.json").write_bytes(saved[name])
        self.anchor["expansion_study"]["findings_sha256"]=publication.sha(saved[name])
        self.repack(saved)
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_publication_counts_and_evidence_symlinks_rejected(self):
        self.publication["expansion_study_games"] += 1
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()
        self.publication=copy.deepcopy(self.payload["publication"])
        file=self.evidence/"expansion-findings.json";file.unlink();file.symlink_to(self.evidence_source/file.name)
        with self.assertRaises(publication.ExpansionPublicationError):self.verify()

    def test_derived_bound_rounding_tolerance_does_not_accept_count_changes(self):
        expected={"confirmation_pairs":[{"normal_family_lower":.2,"first_wins":5}]}
        saved=copy.deepcopy(expected);saved["confirmation_pairs"][0]["normal_family_lower"]+=1e-15
        publication._same(saved,expected)
        saved["confirmation_pairs"][0]["first_wins"]+=1
        with self.assertRaises(publication.ExpansionPublicationError):publication._same(saved,expected)


if __name__=="__main__":
    unittest.main()
