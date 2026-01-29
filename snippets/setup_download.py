"""Download Workshop Materials - Condensed Script

Copy-paste friendly script to download AI Data Analyst Workshop materials.
Works in Databricks notebooks or locally.
"""

import os
import subprocess

# === CONFIGURATION ===
REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "latest"
TARGET_PATH = None  # Auto-detected if None


# === FUNCTIONS ===
def get_latest_version(repo: str) -> str | None:
    """Get the latest release version from GitHub API.

    Args:
        repo: GitHub repo in format "owner/repo"

    Returns:
        Version string (e.g., "v1.0") or None if failed
    """
    import json
    import urllib.request

    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            tag = data.get("tag_name", "")
            # Handle both "workshop-v1.0" and "v1.0" tag formats
            if tag.startswith("workshop-"):
                return tag.replace("workshop-", "")
            return tag
    except Exception as e:
        print(f"Could not fetch latest version: {e}")
        return None


def download_workshop_materials(version: str, target_path: str) -> bool:
    """Download and extract workshop materials from GitHub Releases."""
    url = f"https://github.com/{REPO}/releases/download/workshop-{version}/workshop-materials-{version}.tar.gz"
    print(f"Downloading {version} to {target_path}...")

    try:
        os.makedirs(target_path, exist_ok=True)
        result = subprocess.run(
            f"curl -sL {url} | tar -xz -C {target_path} --strip-components=1",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return False
        print("Download complete!")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_download(target_path: str) -> bool:
    """Verify workshop materials exist."""
    expected = ["src", "notebooks", "scripts", "config", "docs", "pyproject.toml", "README.md"]

    if not os.path.exists(target_path):
        print(f"ERROR: {target_path} does not exist")
        return False

    actual = os.listdir(target_path)
    missing = [item for item in expected if item not in actual]

    print(f"\nContents of {target_path}:")
    for item in sorted(actual):
        path = os.path.join(target_path, item)
        suffix = f"/ ({len(os.listdir(path))} items)" if os.path.isdir(path) else f" ({os.path.getsize(path):,} bytes)"
        print(f"  {item}{suffix}")

    if missing:
        print(f"\nMissing: {missing}")
        return False

    print("\nAll expected items present!")
    return True


# === EXECUTE ===
if __name__ == "__main__":
    IN_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ

    # Determine target path
    if TARGET_PATH:
        target = TARGET_PATH
    elif IN_DATABRICKS:
        user = spark.sql("SELECT current_user()").first()[0]  # noqa: F821
        target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"
    else:
        target = os.path.join(os.getcwd(), "ai-data-analyst-workshop")

    print(f"Environment: {'Databricks' if IN_DATABRICKS else 'Local'}")

    # Resolve "latest" to actual version
    version = VERSION
    if version == "latest":
        print("Fetching latest release version...")
        version = get_latest_version(REPO)
        if not version:
            print("Failed to get latest version, falling back to v1.0")
            version = "v1.0"
        print(f"Latest version: {version}")

    if download_workshop_materials(version, target):
        verify_download(target)
        print(f"\nWorkshop materials ready at: {target}")
    else:
        print(f"\nDownload failed. Check: https://github.com/{REPO}/releases")
