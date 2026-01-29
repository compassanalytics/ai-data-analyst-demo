"""Download Workshop Materials - Condensed Script

Copy-paste friendly script to download AI Data Analyst Workshop materials.
Works in Databricks notebooks or locally.
"""

import os
import subprocess

# === CONFIGURATION ===
REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "v1.0"
TARGET_PATH = None  # Auto-detected if None

# === FUNCTIONS ===


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

    if download_workshop_materials(VERSION, target):
        verify_download(target)
        print(f"\nWorkshop materials ready at: {target}")
    else:
        print(f"\nDownload failed. Check: https://github.com/{REPO}/releases")
