"""
data/fetcher.py
GitHub data fetcher using PyGithub with local JSON caching.
"""

import os
import json
import time
from datetime import datetime, timezone
from github import Github, GithubException, RateLimitExceededException

from config import CACHE_DIR, CACHE_TTL_HOURS, LDA_MAX_COMMITS


class GitHubFetcher:
    def __init__(self, token: str):
        self.g = Github(token, per_page=100)

    # ------------------------------------------------------------------ #
    #  Cache helpers
    # ------------------------------------------------------------------ #
    def _cache_path(self, username: str) -> str:
        os.makedirs(CACHE_DIR, exist_ok=True)
        return os.path.join(CACHE_DIR, f"{username}.json")

    def _load_cache(self, username: str):
        path = self._cache_path(username)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        age_hours = (datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if age_hours > CACHE_TTL_HOURS:
            return None
        return data

    def _save_cache(self, username: str, data: dict):
        path = self._cache_path(username)
        data["_cached_at"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # ------------------------------------------------------------------ #
    #  Public entry point
    # ------------------------------------------------------------------ #
    def get_user_data(self, username: str) -> dict:
        """Return rich dict for *username*. Uses cache if fresh."""
        cached = self._load_cache(username)
        if cached:
            return cached

        data = self._fetch(username)
        self._save_cache(username, data)
        return data

    # ------------------------------------------------------------------ #
    #  Fetching
    # ------------------------------------------------------------------ #
    def _fetch(self, username: str) -> dict:
        try:
            user = self.g.get_user(username)
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"GitHub user '{username}' not found.")
            raise RuntimeError(f"GitHub API error: {e.data.get('message', str(e))}")

        profile = {
            "login": user.login,
            "name": user.name or user.login,
            "bio": user.bio or "",
            "avatar_url": user.avatar_url,
            "public_repos": user.public_repos,
            "followers": user.followers,
            "following": user.following,
            "created_at": str(user.created_at),
            "location": user.location or "",
            "blog": user.html_url,
        }

        repos_data = []
        all_commits = []
        lang_totals: dict[str, int] = {}

        try:
            repos = list(user.get_repos(type="public"))
        except RateLimitExceededException:
            raise RuntimeError("GitHub rate limit exceeded. Please wait or use a different token.")

        for index, repo in enumerate(repos):
            if repo.fork:   # skip forks to focus on own work
                continue

            # ---- language bytes ----
            try:
                langs = repo.get_languages()
            except GithubException:
                langs = {}
            for lang, bcount in langs.items():
                try:
                    lang_totals[lang] = lang_totals.get(lang, 0) + int(bcount)
                except (TypeError, ValueError):
                    pass  # skip non-numeric entries (e.g. URL strings from some PyGithub versions)

            # ---- README presence ----
            has_readme = False
            try:
                repo.get_readme()
                has_readme = True
            except GithubException:
                pass

            # ---- commits (capped to avoid huge repos) ----
            repo_commits = []
            if len(all_commits) < LDA_MAX_COMMITS:
                try:
                    for commit in repo.get_commits(author=username):
                        if len(all_commits) >= LDA_MAX_COMMITS:
                            break
                        # author can be None for orphan/bot commits
                        author_info = commit.commit.author
                        if author_info is None or author_info.date is None:
                            continue
                        ts = author_info.date
                        message = commit.commit.message or ""
                        repo_commits.append({
                            "message": message.split("\n")[0],
                            "timestamp": str(ts),
                            "hour": int(ts.hour),
                            "weekday": ts.strftime("%A"),
                        })
                    all_commits.extend(repo_commits)
                except Exception:
                    pass

            # ---- Repo Health Signals ----
            has_license = False
            has_ci = False
            has_tests = False
            recently_active = False
            low_open_issues = True

            # 1. License
            try:
                repo.get_license()
                has_license = True
            except GithubException:
                pass

            # 2. Issues check
            if repo.has_issues:
                if repo.open_issues_count > 10:
                    low_open_issues = False
            
            # 3. Recency
            if repo.pushed_at:
                days_since_push = (datetime.now(timezone.utc) - repo.pushed_at.replace(tzinfo=timezone.utc)).days
                recently_active = (days_since_push < 90)

            # Deep checks (CI and Tests) - throttled to 20 repos to save rate limit
            if index < 20:
                try:
                    # Check for CI (.github/workflows)
                    try:
                        repo.get_contents(".github/workflows")
                        has_ci = True
                    except GithubException:
                        pass
                    
                    # Check for Tests (top-level files matching patterns)
                    try:
                        contents = repo.get_contents("")
                        test_patterns = ["test", "spec", "jest", "pytest", "unit", "e2e"]
                        for item in contents:
                            if any(p in item.name.lower() for p in test_patterns):
                                has_tests = True
                                break
                    except GithubException:
                        pass
                except Exception:
                    pass

            repos_data.append({
                "name": repo.name,
                "language": repo.language or "Unknown",
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "created_at": str(repo.created_at),
                "updated_at": str(repo.updated_at),
                "has_readme": has_readme,
                "commit_count": len(repo_commits),
                "has_license": has_license,
                "has_ci": has_ci,
                "has_tests": has_tests,
                "recently_active": recently_active,
                "low_open_issues": low_open_issues,
            })

        # ---- issues & PRs authored ----
        issues_authored = 0
        prs_authored = 0
        try:
            issues_authored = int(self.g.search_issues(f"author:{username} is:issue").totalCount)
            prs_authored = int(self.g.search_issues(f"author:{username} is:pr").totalCount)
        except Exception:
            pass

        return {
            "profile": profile,
            "repos": repos_data,
            "commits": all_commits,
            "lang_totals": lang_totals,
            "issues_authored": issues_authored,
            "prs_authored": prs_authored,
        }
