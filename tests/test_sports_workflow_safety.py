"""Regression tests that prevent unsafe Sports HULK GitHub deployment."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ARCHIVED = ROOT / "docs" / "archived-workflows" / "2026-10-07"
PREFLIGHT = ROOT / "scripts" / "sports_deploy_preflight.py"

LEGACY_WRITE_WORKFLOWS = {
    "sports-hulk-ci.yml",
    "sports-hulk-command-center-v2.yml",
    "sports-hulk-final-polish-build.yml",
    "sports-hulk-final-source-repair.yml",
    "sports-hulk-final-ui-build.yml",
    "sports-hulk-force-live-rebuild.yml",
    "sports-hulk-hard-cutover.yml",
    "sports-hulk-mockup-match.yml",
    "sports-hulk-phase2-build.yml",
    "sports-hulk-phase3-build.yml",
    "sports-hulk-promote-final-build.yml",
    "sports-hulk-visual-refresh.yml",
    "sports-hulk-workflow-cleanup.yml",
}


def commands(*parts: str, cwd=None) -> str:
    return subprocess.check_output(list(parts), cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


class WorkflowSafetyTests(unittest.TestCase):
    def test_only_five_approved_workflows_remain_active(self):
        names = {p.name for p in WORKFLOWS.glob("*.yml")}
        self.assertEqual(
            names,
            {
                "sports-hulk-ci-main.yml", "sports-hulk-deploy.yml",
                "sports-hulk-live-diagnostic.yml",
                "sports-hulk-render-trace.yml", "oracle-emergency-recovery.yml",
            },
        )
        self.assertTrue(LEGACY_WRITE_WORKFLOWS.isdisjoint(names))
        self.assertTrue(all((ARCHIVED / name).is_file() for name in LEGACY_WRITE_WORKFLOWS))

    def test_deploy_workflow_manual_only_and_never_writes_live(self):
        content = (WORKFLOWS / "sports-hulk-deploy.yml").read_text()
        event_section = content.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("workflow_dispatch:", event_section)
        self.assertNotIn("push:", event_section)
        self.assertNotIn("workflow_run:", event_section)
        self.assertNotIn("schedule:", event_section)
        for forbidden in ("--delete", "rsync -a", "sudo systemctl", "git reset --hard", "git push", "scp ", "ssh "):
            self.assertNotIn(forbidden, "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("#")))

    def test_push_ci_is_real_testing_and_never_deployment(self):
        ci = (WORKFLOWS / "sports-hulk-ci-main.yml").read_text()
        self.assertIn("push:", ci)
        self.assertIn("node --test", ci)
        self.assertIn("npm run build", ci)
        self.assertIn("test_*regime*.py", ci)
        self.assertIn("test_sports_workflow_safety.py", ci)
        self.assertNotIn("--delete", ci)
        self.assertNotIn("systemctl restart", ci)
        self.assertNotIn("workflow_run:", ci)


class ReadOnlyPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.origin = base / "origin.git"
        self.seed = base / "seed"
        self.live = base / "live"
        commands("git", "init", "--bare", "--initial-branch=main", str(self.origin))
        commands("git", "clone", str(self.origin), str(self.seed))
        commands("git", "config", "user.name", "Sports Safety Test", cwd=self.seed)
        commands("git", "config", "user.email", "safety@example.invalid", cwd=self.seed)
        (self.seed / "README.md").write_text("v1\n")
        commands("git", "add", "README.md", cwd=self.seed)
        commands("git", "commit", "-m", "initial", cwd=self.seed)
        commands("git", "push", "origin", "main", cwd=self.seed)
        commands("git", "clone", str(self.origin), str(self.live))
        commands("git", "config", "user.name", "Sports Safety Test", cwd=self.live)
        commands("git", "config", "user.email", "safety@example.invalid", cwd=self.live)

    def new_remote_commit(self, name="README.md", content="v2\n"):
        file = self.seed / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        commands("git", "add", name, cwd=self.seed)
        commands("git", "commit", "-m", "remote update", cwd=self.seed)
        commands("git", "push", "origin", "main", cwd=self.seed)
        commands("git", "fetch", "origin", "main", cwd=self.live)

    def preflight(self):
        p = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--root", str(self.live), "--json"],
            text=True, capture_output=True,
        )
        return p, json.loads(p.stdout)

    def test_safe_remote_update_preserves_local_data(self):
        self.new_remote_commit("README.md", "v2\n")
        (self.live / "research_ledger.jsonl").write_text("my-history\n")
        before = commands("git", "rev-parse", "HEAD", cwd=self.live)
        process, report = self.preflight()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(report["status"], "PREFLIGHT_PASS")
        self.assertEqual(commands("git", "rev-parse", "HEAD", cwd=self.live), before)
        self.assertEqual((self.live / "research_ledger.jsonl").read_text(), "my-history\n")

    def test_blocks_uncommitted_frontend(self):
        self.new_remote_commit()
        f = self.live / "commercial_web" / "src" / "App.jsx"
        f.parent.mkdir(parents=True)
        f.write_text("unsaved work\n")
        p, result = self.preflight()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("frontend" in x for x in result["reasons"]))
        self.assertEqual(f.read_text(), "unsaved work\n")

    def test_blocks_collision_with_local_changes(self):
        (self.live / "README.md").write_text("private edit\n")
        self.new_remote_commit("README.md", "remote edit\n")
        p, result = self.preflight()
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(any("conflicts" in x for x in result["reasons"]))

    def test_blocks_diverged_history(self):
        (self.live / "another.txt").write_text("local only")
        commands("git", "add", "another.txt", cwd=self.live)
        commands("git", "commit", "-m", "local commit", cwd=self.live)
        self.new_remote_commit()
        p, result = self.preflight()
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(any("divergent" in x for x in result["reasons"]))

    def test_blocks_deletions(self):
        commands("git", "rm", "README.md", cwd=self.seed)
        commands("git", "commit", "-m", "remote removal", cwd=self.seed)
        commands("git", "push", "origin", "main", cwd=self.seed)
        commands("git", "fetch", "origin", "main", cwd=self.live)
        p, result = self.preflight()
        self.assertNotEqual(p.returncode, 0)
        self.assertTrue(any("deletes" in x for x in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
