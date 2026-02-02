# Troubleshooting Guide

Common issues and solutions for the AI Data Analyst Workshop.

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Genie Issues](#genie-issues)
3. [RAG/Vector Search Issues](#ragvector-search-issues)
4. [Import and Dependency Issues](#import-and-dependency-issues)
5. [Notebook Issues](#notebook-issues)
6. [Data Generation Issues](#data-generation-issues)
7. [Performance Issues](#performance-issues)
8. [Debugging Tips](#debugging-tips)

---

## Authentication Issues

### "Authentication failed" or 401 Errors

**Symptoms:**
```
AuthenticationError: Failed to authenticate with Databricks
```

**Solutions:**

1. **Check DATABRICKS_HOST format:**
   ```bash
   # Must include https://
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com  # Correct
   DATABRICKS_HOST=your-workspace.cloud.databricks.com          # Wrong
   ```

2. **Verify token validity:**
   - Tokens expire - regenerate if needed
   - Go to: Settings > Developer > Access tokens

3. **Check token permissions:**
   - Token needs "Can Use" on Genie Spaces
   - Token needs access to SQL Warehouses

4. **In Databricks notebooks:**
   - Don't set DATABRICKS_TOKEN (automatic auth)
   - Only set DATABRICKS_HOST if needed

### "Token not found" in Local Development

**Symptoms:**
```
Config validation error: DATABRICKS_TOKEN is required
```

**Solutions:**

1. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Verify .env is loaded:**
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   import os
   print(os.getenv("DATABRICKS_TOKEN"))  # Should not be None
   ```

3. **Use mock mode for testing:**
   ```bash
   MOCK_MODE=true uv run python your_script.py
   ```

---

## Genie Issues

### "Genie Space not found"

**Symptoms:**
```
GenieSpaceNotFoundError: Space ID 'abc123' not found
```

**Solutions:**

1. **Verify Space ID:**
   - Navigate to Genie in Databricks
   - Open your space
   - Copy ID from URL: `/genie/spaces/[THIS_ID]/conversations`

2. **Check permissions:**
   - You need "CAN USE" permission on the space
   - Ask space owner to share with you

3. **Verify workspace:**
   - Space must exist in the workspace you're connecting to

### Rate Limit Exceeded (429)

**Symptoms:**
```
RateLimitError: Rate limit exceeded. Please wait before retrying.
```

**Rate Limits:**
- UI: 20 questions/minute
- API: 5 questions/minute

**Solutions:**

1. **Add delays:**
   ```python
   import time
   for question in questions:
       result = agent.query(question)
       time.sleep(12)  # 5 per minute = 12 second intervals
   ```

2. **Enable caching:**
   ```bash
   CACHE_ENABLED=true
   CACHE_TTL_SECONDS=300
   ```

3. **Use mock mode for development:**
   ```bash
   MOCK_MODE=true
   ```

### Genie Returns Wrong Results

**Symptoms:**
- Genie picks wrong columns
- Results don't match expectations
- SQL errors or incorrect aggregations

**Solutions:**

1. **Improve data quality:**
   - See `docs/GENIE_BEST_PRACTICES.md`
   - Remove ambiguous columns (e.g., 7 revenue columns)
   - Use clear column names

2. **Add Knowledge Store entries:**
   - Define SQL expressions for metrics
   - Add system instructions with business context
   - Provide sample questions

3. **Check your data:**
   ```sql
   -- In Databricks SQL
   DESCRIBE TABLE your_table;
   SELECT * FROM your_table LIMIT 10;
   ```

### "Conversation timed out"

**Symptoms:**
```
TimeoutError: Genie conversation did not complete within 120 seconds
```

**Solutions:**

1. **Increase timeout:**
   ```python
   result = agent.query(question, timeout_seconds=300)
   ```

2. **Simplify query:**
   - Break complex questions into simpler parts
   - Reduce data scope (add filters)

3. **Check warehouse status:**
   - SQL Warehouse might be starting up
   - Warehouse might be overloaded

---

## RAG/Vector Search Issues

### "Vector Search endpoint not found"

**Symptoms:**
```
ResourceNotFoundError: Vector Search endpoint 'xyz' not found
```

**Solutions:**

1. **Create endpoint:**
   ```bash
   uv run python scripts/setup_vector_search.py
   ```

2. **Check endpoint name:**
   ```bash
   # List endpoints
   databricks vector-search list-endpoints
   ```

3. **Verify configuration:**
   ```bash
   # In .env
   VECTOR_SEARCH_ENDPOINT=your-actual-endpoint-name
   ```

### "Vector Search index not found"

**Symptoms:**
```
IndexNotFoundError: Index 'catalog.schema.index' not found
```

**Solutions:**

1. **Check full index name:**
   - Format: `catalog.schema.index_name`
   - Example: `workspace.rag_demo.document_index`

2. **Create index:**
   ```bash
   uv run python scripts/setup_vector_search.py
   ```

3. **Verify index exists:**
   - Compute > Vector Search > Your endpoint > Indexes

### RAG Returns Empty Results

**Solutions:**

1. **Check if documents are indexed:**
   ```python
   # Query the source table
   df = spark.sql("SELECT COUNT(*) FROM workspace.rag_demo.document_chunks")
   df.show()
   ```

2. **Load documents:**
   ```bash
   uv run python scripts/load_documents.py
   ```

3. **Check embedding model:**
   ```bash
   # Verify endpoint exists
   EMBEDDING_ENDPOINT=databricks-bge-large-en
   ```

---

## Import and Dependency Issues

### "ModuleNotFoundError"

**Symptoms:**
```
ModuleNotFoundError: No module named 'databricks_langchain'
```

**Solutions:**

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Verify installation:**
   ```bash
   uv pip list | grep databricks
   ```

3. **In Databricks notebooks:**
   ```python
   %pip install databricks-langchain langgraph
   dbutils.library.restartPython()
   ```

### "ImportError: cannot import name"

**Symptoms:**
```
ImportError: cannot import name 'GenieDataAgent' from 'src.agents'
```

**Solutions:**

1. **Check __init__.py exports:**
   - Ensure class is exported in `src/agents/__init__.py`

2. **Restart Python:**
   - In notebooks: `dbutils.library.restartPython()`
   - Locally: restart your Python process

3. **Check for circular imports:**
   - Use `TYPE_CHECKING` for type hints
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from src.agents.genie_agent import GenieResult
   ```

### Version Conflicts

**Solutions:**

1. **Clean reinstall:**
   ```bash
   rm -rf .venv
   uv venv
   uv sync
   ```

2. **Check Python version:**
   ```bash
   python --version  # Must be 3.10+
   ```

---

## Notebook Issues

### Notebooks Won't Import src/

**In Databricks notebooks:**

```python
# Add to path
import sys
sys.path.append('/Workspace/Users/you@company.com/ai-data-analyst-demo')

# Now imports work
from src.config import Config
```

### Widgets Not Working

**Symptoms:**
- dbutils.widgets not defined
- Widget values not updating

**Solutions:**

1. **Create widgets first:**
   ```python
   dbutils.widgets.text("genie_space_id", "", "Genie Space ID")
   ```

2. **Access values:**
   ```python
   space_id = dbutils.widgets.get("genie_space_id")
   ```

3. **Remove widgets to reset:**
   ```python
   dbutils.widgets.removeAll()
   ```

### "Cluster not found"

**Solutions:**

1. **Start cluster:**
   - Compute > Select cluster > Start

2. **Attach notebook:**
   - Click cluster dropdown in notebook
   - Select running cluster

3. **Use serverless:**
   - Some notebooks support serverless compute

---

## Data Generation Issues

### "Data directory not found"

**Solutions:**

1. **Create directories:**
   ```bash
   mkdir -p dataset_generators/data
   ```

2. **Run from project root:**
   ```bash
   cd ai-data-analyst-workshop
   uv run python dataset_generators/generate_velocity_motors.py
   ```

### Generated Data Has Issues

**Solutions:**

1. **Check parameters:**
   ```bash
   uv run python dataset_generators/generate_velocity_motors.py --help
   ```

2. **Set seed for reproducibility:**
   ```python
   # In generator
   import random
   random.seed(42)
   ```

3. **Regenerate with clean slate:**
   ```bash
   rm -rf dataset_generators/data/velocity_motors
   uv run python dataset_generators/generate_velocity_motors.py
   ```

---

## Performance Issues

### Slow Query Response

**Solutions:**

1. **Enable caching:**
   ```bash
   CACHE_ENABLED=true
   CACHE_TTL_SECONDS=600  # 10 minutes
   ```

2. **Use parallel queries:**
   ```python
   result = orchestrator.query_spaces(question, parallel=True)
   ```

3. **Check warehouse size:**
   - Scale up warehouse for better performance
   - SQL Warehouses > Your warehouse > Edit > Size

### Memory Issues

**Solutions:**

1. **Limit result rows:**
   ```python
   print(result.to_markdown_table(max_rows=50))
   ```

2. **Process in batches:**
   ```python
   for batch in batched(questions, size=10):
       # Process batch
       pass
   ```

---

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Configuration

```python
from src.config import Config
config = Config.from_env()
print(config)  # Shows all settings (token hidden)
print(config.validate())  # Shows validation errors
```

### Test Mock Mode First

```bash
MOCK_MODE=true uv run python -c "
from src.config import Config
from src.agents.genie_agent import GenieDataAgent

config = Config.from_env()
print(f'Mock mode: {config.mock_mode}')

agent = GenieDataAgent(config)
result = agent.query('test')
print(f'Success: {result.success}')
"
```

### Clear Caches

```python
from src.config import clear_config_cache
clear_config_cache()
```

### Check Databricks Connection

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
print(f"Connected to: {w.config.host}")
print(f"User: {w.current_user.me().user_name}")
```

---

## Getting Help

1. **Check existing docs:**
   - `docs/SETUP.md` - Setup guide
   - `docs/ARCHITECTURE.md` - How it works
   - `docs/GENIE_BEST_PRACTICES.md` - Data quality

2. **Databricks resources:**
   - [Genie Documentation](https://docs.databricks.com/aws/en/genie/)
   - [Vector Search Docs](https://docs.databricks.com/aws/en/generative-ai/vector-search/)

3. **LangGraph resources:**
   - [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
