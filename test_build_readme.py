import unittest

import build_readme


def pr(repo, title, merged_at):
    return {
        "repository_url": f"https://api.github.com/repos/{repo}",
        "title": title,
        "html_url": f"https://github.com/{repo}/pull/1",
        "pull_request": {"merged_at": merged_at},
    }


class ReplaceSectionTest(unittest.TestCase):
    def test_replaces_only_the_named_section(self):
        text = "a\n<!-- x starts -->\nold\n<!-- x ends -->\nb\n<!-- y starts -->\nkeep\n<!-- y ends -->"
        result = build_readme.replace_section(text, "x", "new")
        self.assertIn("<!-- x starts -->\nnew\n<!-- x ends -->", result)
        self.assertIn("keep", result)
        self.assertNotIn("old", result)

    def test_body_with_backslashes_is_kept_literally(self):
        text = "<!-- x starts --><!-- x ends -->"
        result = build_readme.replace_section(text, "x", r"C:\path \1")
        self.assertIn(r"C:\path \1", result)

    def test_missing_markers_fail_loudly(self):
        with self.assertRaises(ValueError):
            build_readme.replace_section("no markers here", "x", "new")


class UpstreamTest(unittest.TestCase):
    def test_skips_own_owners_and_awesome_lists(self):
        prs = [
            pr("immich-app/immich", "fix", "2026-09-01T00:00:00Z"),
            pr("justadityaraj/foldout", "mine", "2026-10-01T00:00:00Z"),
            pr("punkpeye/awesome-mcp-servers", "list entry", "2026-10-02T00:00:00Z"),
        ]
        self.assertEqual([p["title"] for p in build_readme.upstream(prs)], ["fix"])

    def test_recent_merges_are_newest_first(self):
        prs = [
            pr("a/one", "older", "2026-09-01T00:00:00Z"),
            pr("b/two", "newer", "2026-10-01T00:00:00Z"),
        ]
        lines = build_readme.merged_lines(build_readme.upstream(prs), limit=5)
        self.assertTrue(lines[0].startswith("[two: Newer]"))
        self.assertIn("2026-10-01", lines[0])

    def test_titles_drop_commit_prefixes_and_closes_refs(self):
        self.assertEqual(
            build_readme.clean_title("feat(permissions): union mode for --permissions (closes #808)"),
            "Union mode for --permissions",
        )
        self.assertEqual(build_readme.clean_title("fix: windows file uploads"), "Windows file uploads")
        self.assertEqual(build_readme.clean_title("Keep commas in search"), "Keep commas in search")


class ReleaseNameTest(unittest.TestCase):
    def test_uses_release_name_when_it_names_the_app(self):
        self.assertEqual(build_readme.release_label("foldout", "Foldout 0.1.3", "v0.1.3"), "Foldout 0.1.3")

    def test_falls_back_to_repo_and_tag_for_bare_version_names(self):
        self.assertEqual(
            build_readme.release_label("amazon-in-mcp", "v0.1.3 - routing", "v0.1.3"), "amazon-in-mcp v0.1.3"
        )


if __name__ == "__main__":
    unittest.main()
