# Workshop Setup Guide

Download and set up the AI Data Analyst Workshop materials.

## Quick Start (Databricks)

Run this in a Databricks notebook cell:

```python
# Download Workshop Materials
WORKSHOP_VERSION = "v1.0"
REPO = "compassanalytics/ai-data-analyst-demo"

import subprocess
user = spark.sql("SELECT current_user()").first()[0]
target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"

subprocess.run(["mkdir", "-p", target], check=True)
subprocess.run(
    f"curl -sL https://github.com/{REPO}/releases/download/workshop-{WORKSHOP_VERSION}/workshop-materials-{WORKSHOP_VERSION}.tar.gz | tar -xz -C {target} --strip-components=1",
    shell=True, check=True
)
print(f"Workshop materials downloaded to: {target}")
```

## Alternative: Git Clone

If you have repository access:

```python
!pip install gitpython -q

import git
user = spark.sql("SELECT current_user()").first()[0]
target = f"/Workspace/Users/{user}/ai-data-analyst-workshop"

git.Repo.clone_from(
    "https://github.com/compassanalytics/ai-data-analyst-demo.git",
    target,
    branch="main"
)
print(f"Repository cloned to: {target}")
```

## Local Setup

```bash
# Download release
curl -sL https://github.com/compassanalytics/ai-data-analyst-demo/releases/download/workshop-v1.0/workshop-materials-v1.0.tar.gz | tar -xz

# Or clone repository
git clone https://github.com/compassanalytics/ai-data-analyst-demo.git
cd ai-data-analyst-demo

# Install dependencies
uv sync
```

## For Release Managers

### Creating a New Release

```bash
# Tag and push
git tag workshop-v1.0
git push origin workshop-v1.0

# GitHub Actions will automatically create the release
```

### Manual Release

Go to Actions -> "Release Workshop Materials" -> Run workflow -> Enter version.

## Versioning

| Tag | Description |
|-----|-------------|
| `workshop-v1.0` | Initial stable release |
| `workshop-v1.1` | Bug fixes, minor updates |
| `workshop-v2.0` | Major changes |

## Troubleshooting

### "Permission denied" on Databricks
- Ensure you have write access to your user workspace
- Try: `/Workspace/Users/your-email@domain.com/workshop`

### curl: command not found
- Use the Python `requests` library instead
- Or install via `%sh apt-get install curl`

### Release not found (404)
- Check the version exists: https://github.com/compassanalytics/ai-data-analyst-demo/releases
- Verify the tag format: `workshop-v1.0` (not `v1.0`)

## Next Steps

After downloading:
1. Open `notebooks/00b_setup_data.ipynb` to set up data
2. Run `notebooks/01_agent_basics.ipynb` for the main demonstration
3. Try `notebooks/03_build_your_agent.ipynb` for hands-on challenges
