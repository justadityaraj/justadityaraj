import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

USER = "justadityaraj"
OWN_OWNERS = ("justadityaraj", "bncwin", "swagloop", "briefs-finance")
FEED = "https://adityarajsingh.com/feed/"
README = Path(__file__).parent / "README.md"


def fetch(url):
    headers = {"User-Agent": USER, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        return resp.read()


def github(path, **params):
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    return json.loads(fetch(f"https://api.github.com{path}{query}"))


def replace_section(text, name, body):
    pattern = re.compile(rf"(<!-- {name} starts -->).*?(<!-- {name} ends -->)", re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"README has no {name} markers")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)


def repo_of(pr):
    return pr["repository_url"].split("/repos/", 1)[1]


def merged_on(pr):
    return (pr["pull_request"].get("merged_at") or pr.get("closed_at"))[:10]


def upstream(prs):
    return [
        p
        for p in prs
        if repo_of(p).split("/")[0] not in OWN_OWNERS and not repo_of(p).split("/")[1].startswith("awesome")
    ]


def clean_title(title):
    title = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", title)
    title = re.sub(r"\s*\((closes|fixes) #\d+\)$", "", title)
    return title[:1].upper() + title[1:]


def dated(link, iso_date):
    day = date.fromisoformat(iso_date)
    return f"{link}<br><sub>{day.day} {day:%b %Y}</sub>"


def merged_lines(prs, limit):
    recent = sorted(prs, key=merged_on, reverse=True)[:limit]
    return [
        dated(f"[{repo_of(p).split('/')[1]}: {clean_title(p['title'])}]({p['html_url']})", merged_on(p)) for p in recent
    ]


def release_label(repo, name, tag):
    return name if name and not re.match(r"v?\d", name) else f"{repo} {tag}"


def merged_prs():
    query = f"author:{USER} is:pr is:merged " + " ".join(f"-user:{owner}" for owner in OWN_OWNERS)
    prs, page = [], 1
    while True:
        result = github("/search/issues", q=query, per_page=100, page=page)
        prs += result["items"]
        if not result["items"] or len(prs) >= result["total_count"]:
            return prs
        page += 1


def release_lines(limit):
    releases = []
    for repo in github(f"/users/{USER}/repos", type="owner", per_page=100):
        if repo["fork"] or repo["private"]:
            continue
        published = [r for r in github(f"/repos/{repo['full_name']}/releases", per_page=10) if not (r["draft"] or r["prerelease"])]
        if published:
            rel = published[0]
            label = release_label(repo["name"], rel["name"], rel["tag_name"])
            published_on = rel["published_at"][:10]
            releases.append((published_on, dated(f"[{label}]({rel['html_url']})", published_on)))
    return [line for _, line in sorted(releases, reverse=True)[:limit]]


def stats_line(prs):
    return f"Contributing to **{len({repo_of(p) for p in prs})} open-source projects** whenever I get the chance."


def blog_lines(limit):
    items = ET.fromstring(fetch(FEED)).iter("item")
    return [f"[{item.findtext('title')}]({item.findtext('link')})" for item in list(items)[:limit]]


def main():
    prs = upstream(merged_prs())
    text = README.read_text(encoding="utf-8")
    text = replace_section(text, "stats", stats_line(prs))
    text = replace_section(text, "releases", "\n\n".join(release_lines(6)))
    text = replace_section(text, "merged", "\n\n".join(merged_lines(prs, 6)))
    text = replace_section(text, "blog", "\n\n".join(blog_lines(5)))
    README.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
