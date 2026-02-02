# Download AI Data Analyst Workshop materials — copy-paste into a Databricks notebook cell
import json
import os
import subprocess
import urllib.request

REPO = "compassanalytics/ai-data-analyst-demo"
VERSION = "latest"  # or pin to e.g. "v1.4"
TARGET_PATH = None  # auto-detected if None

# --- resolve target path ---
IN_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ
if TARGET_PATH:
    target = TARGET_PATH
elif IN_DATABRICKS:
    user = spark.sql("SELECT current_user()").first()[0]  # noqa: F821
    target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"
else:
    target = os.path.join(os.getcwd(), "ai-data-analyst-workshop")

# --- resolve version ---
version = VERSION
if version == "latest":
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            tag = json.loads(resp.read().decode()).get("tag_name", "")
            version = tag.replace("workshop-", "") if tag.startswith("workshop-") else tag
    except Exception as e:
        print(f"Could not fetch latest version ({e}), falling back to v1.0")
        version = "v1.0"

# --- download & extract ---
url = f"https://github.com/{REPO}/releases/download/workshop-{version}/workshop-materials-{version}.tar.gz"
print(f"Downloading {version} to {target} ...")
os.makedirs(target, exist_ok=True)
r = subprocess.run(
    f"curl -sL {url} | tar -xz -C {target} --strip-components=1", shell=True, capture_output=True, text=True
)
if r.returncode != 0:
    raise RuntimeError(f"Download failed: {r.stderr}\nCheck: https://github.com/{REPO}/releases")

# --- verify ---
expected = {
    "src",
    "notebooks",
    "config",
    "infra",
    "docs",
    "pyproject.toml",
    "README.md",
    "databricks.yml",
    ".env.example",
}
actual = set(os.listdir(target))
missing = expected - actual
for item in sorted(actual):
    p = os.path.join(target, item)
    info = f"/ ({len(os.listdir(p))} items)" if os.path.isdir(p) else f" ({os.path.getsize(p):,} bytes)"
    print(f"  {item}{info}")
if missing:
    print(f"\n⚠ Missing: {sorted(missing)}")
else:
    print(f"\nWorkshop materials ready at: {target}")
