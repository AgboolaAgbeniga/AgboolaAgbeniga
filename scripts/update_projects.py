"""
Auto-update README.md with pinned GitHub repositories.

Fetches pinned repos (name, description, homepage/live link, topics)
via the GitHub GraphQL API and injects them into README.md between
<!-- PROJECTS:START --> and <!-- PROJECTS:END --> markers.

Required env var:  GH_TOKEN  (GitHub Personal Access Token with read:user scope)
"""

import os
import re
import sys
import requests

GITHUB_USERNAME = "AgboolaAgbeniga"
GRAPHQL_URL = "https://api.github.com/graphql"
README_PATH = "README.md"

QUERY = """
query {
  user(login: "%s") {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          homepageUrl
          stargazerCount
          primaryLanguage {
            name
          }
          repositoryTopics(first: 5) {
            nodes {
              topic {
                name
              }
            }
          }
        }
      }
    }
  }
}
""" % GITHUB_USERNAME


def fetch_pinned_repos(token: str) -> list[dict]:
    """Fetch pinned repositories from GitHub GraphQL API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY},
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")

    return data["data"]["user"]["pinnedItems"]["nodes"]


def build_tech_stack(repo: dict) -> str:
    """Build a tech stack string from topics and primary language."""
    topics = [
        node["topic"]["name"]
        for node in repo.get("repositoryTopics", {}).get("nodes", [])
    ]
    lang = (repo.get("primaryLanguage") or {}).get("name", "")

    # Prefer topics (more descriptive), fall back to language
    stack_items = topics[:4] if topics else ([lang] if lang else [])
    return ", ".join(stack_items) if stack_items else "—"


def build_project_row(repo: dict) -> str:
    """Build a single markdown table row for a repository."""
    name = repo["name"]
    description = (repo.get("description") or "No description provided.").strip()
    github_url = repo["url"]
    homepage = (repo.get("homepageUrl") or "").strip()
    tech = build_tech_stack(repo)
    stars = repo.get("stargazerCount", 0)

    # Name cell: live link + source link
    if homepage:
        name_cell = f"**[{name}]({homepage})** · [Source]({github_url})"
    else:
        name_cell = f"**[{name}]({github_url})**"

    # Append star count if > 0
    star_suffix = f" ⭐ {stars}" if stars > 0 else ""

    return f"| {name_cell}{star_suffix} | {description} | {tech} |"


def generate_projects_section(repos: list[dict]) -> str:
    """Generate the full markdown projects table."""
    header = "| Project | Description | Tech Stack |\n| :--- | :--- | :--- |"
    rows = "\n".join(build_project_row(r) for r in repos)
    return f"{header}\n{rows}"


def update_readme(projects_md: str) -> bool:
    """
    Replace content between PROJECTS:START and PROJECTS:END markers.
    Returns True if the file was modified.
    """
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    marker_start = "<!-- PROJECTS:START -->"
    marker_end = "<!-- PROJECTS:END -->"
    new_block = f"{marker_start}\n{projects_md}\n{marker_end}"

    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        flags=re.DOTALL,
    )

    if not pattern.search(content):
        print("❌ ERROR: Could not find PROJECTS:START/END markers in README.md")
        sys.exit(1)

    new_content = pattern.sub(new_block, content)

    if new_content == content:
        print("✅ No changes detected — README is already up to date.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ README.md updated successfully!")
    return True


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("❌ ERROR: GH_TOKEN environment variable is not set.")
        print("   Create a PAT at https://github.com/settings/tokens")
        print("   Required scopes: read:user, public_repo")
        sys.exit(1)

    print(f"🔍 Fetching pinned repos for @{GITHUB_USERNAME}...")
    repos = fetch_pinned_repos(token)

    if not repos:
        print("⚠️  No pinned repositories found. Pin some repos on your GitHub profile.")
        sys.exit(0)

    print(f"📦 Found {len(repos)} pinned repo(s): {[r['name'] for r in repos]}")

    projects_md = generate_projects_section(repos)
    update_readme(projects_md)


if __name__ == "__main__":
    main()
