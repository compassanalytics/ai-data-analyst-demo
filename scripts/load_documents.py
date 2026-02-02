#!/usr/bin/env python
"""Load documents into Delta table for RAG Vector Search.

Reads markdown documents, chunks them, and loads into the Delta table.
Embeddings are generated automatically by the Vector Search index (managed embeddings).

Usage:
    # Dry run - show what would be loaded
    uv run python scripts/load_documents.py --dry-run

    # Load documents
    uv run python scripts/load_documents.py

    # Custom documents directory
    uv run python scripts/load_documents.py --docs-dir /path/to/docs

    # Sync index after loading
    uv run python scripts/load_documents.py --sync
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Default configuration (can be overridden by environment variables)
import os

from src.config import Config

DEFAULT_DOCS_DIR = Path(__file__).parent.parent / "data" / "documents"
DEFAULT_CATALOG = os.getenv("VS_CATALOG", "workspace")
DEFAULT_SCHEMA = os.getenv("VS_SCHEMA", "rag_demo")
DEFAULT_TABLE = os.getenv("VS_TABLE", "document_chunks")
DEFAULT_INDEX = os.getenv("VS_INDEX", "document_index")

# Chunking parameters
DEFAULT_CHUNK_SIZE = 1000  # characters
DEFAULT_CHUNK_OVERLAP = 200  # characters


def generate_chunk_id(content: str, source: str, position: int) -> str:
    """Generate a unique ID for a document chunk.

    Args:
        content: Chunk text content
        source: Source document filename
        position: Position of chunk in document

    Returns:
        Unique hash-based ID
    """
    hash_input = f"{source}:{position}:{content[:100]}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def read_markdown_files(docs_dir: Path) -> list[tuple[str, str]]:
    """Read all markdown files from a directory.

    Args:
        docs_dir: Directory containing markdown files

    Returns:
        List of (filename, content) tuples
    """
    documents = []

    if not docs_dir.exists():
        print(f"⚠️  Documents directory not found: {docs_dir}")
        return documents

    for file_path in sorted(docs_dir.glob("*.md")):
        try:
            content = file_path.read_text(encoding="utf-8")
            documents.append((file_path.name, content))
            print(f"   📄 Read: {file_path.name} ({len(content):,} chars)")
        except Exception as e:
            print(f"   ❌ Failed to read {file_path.name}: {e}")

    return documents


def chunk_document(
    content: str,
    source: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Split a document into overlapping chunks.

    Uses RecursiveCharacterTextSplitter for intelligent splitting.

    Args:
        content: Document text content
        source: Source filename
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries with id, content, source, metadata
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )

        texts = splitter.split_text(content)

    except ImportError:
        # Fallback to simple splitting if langchain not available
        print("   ⚠️  langchain-text-splitters not found, using simple splitting")
        texts = simple_chunk(content, chunk_size, chunk_overlap)

    chunks = []
    for i, text in enumerate(texts):
        chunk_id = generate_chunk_id(text, source, i)
        chunks.append(
            {
                "id": chunk_id,
                "content": text.strip(),
                "source": source,
                "metadata": json.dumps(
                    {
                        "position": i,
                        "total_chunks": len(texts),
                        "char_count": len(text),
                    }
                ),
            }
        )

    return chunks


def simple_chunk(content: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple fallback chunking by character count.

    Args:
        content: Text to chunk
        chunk_size: Target chunk size
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]

        # Try to break at paragraph boundary
        if end < len(content):
            last_para = chunk.rfind("\n\n")
            if last_para > chunk_size // 2:
                chunk = content[start : start + last_para]
                end = start + last_para

        chunks.append(chunk)
        start = end - overlap

    return chunks


def load_chunks_to_delta(
    config: Config,
    chunks: list[dict],
    catalog: str,
    schema: str,
    table: str,
    dry_run: bool = False,
) -> bool:
    """Load document chunks to Delta table.

    Args:
        config: Configuration instance
        chunks: List of chunk dictionaries
        catalog: Catalog name
        schema: Schema name
        table: Table name
        dry_run: If True, only print what would be done

    Returns:
        True if successful
    """
    full_name = f"{catalog}.{schema}.{table}"
    print(f"\n📤 Loading {len(chunks)} chunks to {full_name}")

    if dry_run:
        print(f"   [DRY RUN] Would insert {len(chunks)} rows")
        for i, chunk in enumerate(chunks[:3]):
            print(f"   Sample {i + 1}: id={chunk['id']}, source={chunk['source']}, content={chunk['content'][:50]}...")
        if len(chunks) > 3:
            print(f"   ... and {len(chunks) - 3} more")
        return True

    try:
        from databricks.sdk import WorkspaceClient

        client = WorkspaceClient(
            host=config.databricks_host,
            token=config.databricks_token,
        )

        # Clear existing data (optional - could use MERGE instead)
        print("   ⏳ Clearing existing data...")
        client.statement_execution.execute_statement(
            warehouse_id=config.warehouse_id,
            statement=f"TRUNCATE TABLE {full_name}",
            wait_timeout="50s",
        )

        # Insert chunks in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            # Build VALUES clause
            values_list = []
            for chunk in batch:
                # Escape single quotes in content and metadata
                content_escaped = chunk["content"].replace("'", "''")
                source_escaped = chunk["source"].replace("'", "''")
                metadata_escaped = chunk["metadata"].replace("'", "''")

                values_list.append(f"('{chunk['id']}', '{content_escaped}', '{source_escaped}', '{metadata_escaped}')")

            sql = f"""
            INSERT INTO {full_name} (id, content, source, metadata)
            VALUES {", ".join(values_list)}
            """

            client.statement_execution.execute_statement(
                warehouse_id=config.warehouse_id,
                statement=sql,
                wait_timeout="50s",
            )

            print(f"   ... Inserted batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}")

        print(f"   ✅ Loaded {len(chunks)} chunks successfully")
        return True

    except Exception as e:
        print(f"   ❌ Failed to load chunks: {e}")
        return False


def sync_vector_search_index(
    config: Config,
    endpoint_name: str,
    index_name: str,
    dry_run: bool = False,
) -> bool:
    """Trigger sync on Vector Search index.

    Args:
        config: Configuration instance
        endpoint_name: VS endpoint name
        index_name: Full index name (catalog.schema.index)
        dry_run: If True, only print what would be done

    Returns:
        True if successful
    """
    print(f"\n🔄 Syncing Vector Search index: {index_name}")

    if dry_run:
        print(f"   [DRY RUN] Would trigger sync on {index_name}")
        return True

    try:
        from databricks.vector_search.client import VectorSearchClient

        vsc = VectorSearchClient(
            workspace_url=config.databricks_host,
            personal_access_token=config.databricks_token,
        )

        index = vsc.get_index(
            endpoint_name=endpoint_name,
            index_name=index_name,
        )

        # Trigger sync
        print("   ⏳ Triggering sync...")
        index.sync()

        print("   ✅ Sync triggered. Embeddings will be generated automatically.")
        print("   ℹ️  Check sync status in Databricks UI or wait a few minutes.")
        return True

    except Exception as e:
        print(f"   ❌ Failed to sync index: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Load documents into Delta table for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DEFAULT_DOCS_DIR,
        help=f"Documents directory (default: {DEFAULT_DOCS_DIR})",
    )
    parser.add_argument(
        "--catalog",
        default=DEFAULT_CATALOG,
        help=f"Unity Catalog name (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Schema name (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE,
        help=f"Table name (default: {DEFAULT_TABLE})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in characters (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help=f"Chunk overlap in characters (default: {DEFAULT_CHUNK_OVERLAP})",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync Vector Search index after loading",
    )
    parser.add_argument(
        "--endpoint-name",
        default="rag-demo-endpoint",
        help="Vector Search endpoint name for sync",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help=f"Index name for sync (default: {DEFAULT_INDEX})",
    )

    args = parser.parse_args()

    # Load configuration
    print("🔧 Loading configuration...")
    config = Config.from_env()

    # Validate configuration
    if not config.mock_mode and not args.dry_run:
        if not config.databricks_host:
            print("❌ DATABRICKS_HOST is required")
            sys.exit(1)
        if not config.warehouse_id:
            print("❌ WAREHOUSE_ID is required for SQL operations")
            sys.exit(1)

    print("\n📋 Configuration:")
    print(f"   Documents: {args.docs_dir}")
    print(f"   Target: {args.catalog}.{args.schema}.{args.table}")
    print(f"   Chunk size: {args.chunk_size} chars")
    print(f"   Chunk overlap: {args.chunk_overlap} chars")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Step 1: Read documents
    print(f"\n📖 Reading documents from {args.docs_dir}...")
    documents = read_markdown_files(args.docs_dir)

    if not documents:
        print("❌ No documents found. Create markdown files in notebooks/data/documents/")
        sys.exit(1)

    print(f"   Found {len(documents)} documents")

    # Step 2: Chunk documents
    print("\n✂️  Chunking documents...")
    all_chunks = []

    for filename, content in documents:
        chunks = chunk_document(
            content,
            filename,
            args.chunk_size,
            args.chunk_overlap,
        )
        all_chunks.extend(chunks)
        print(f"   {filename}: {len(chunks)} chunks")

    print(f"\n   Total: {len(all_chunks)} chunks from {len(documents)} documents")

    # Step 3: Load to Delta table
    if not load_chunks_to_delta(
        config,
        all_chunks,
        args.catalog,
        args.schema,
        args.table,
        args.dry_run,
    ):
        print("\n❌ Failed to load documents. Aborting.")
        sys.exit(1)

    # Step 4: Sync index (optional)
    if args.sync:
        full_index_name = f"{args.catalog}.{args.schema}.{args.index}"
        if not sync_vector_search_index(
            config,
            args.endpoint_name,
            full_index_name,
            args.dry_run,
        ):
            print("\n⚠️  Index sync failed, but documents were loaded.")

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ DRY RUN COMPLETE - No changes were made")
    else:
        print("✅ DOCUMENT LOADING COMPLETE")
        print(f"\n   Loaded: {len(all_chunks)} chunks from {len(documents)} documents")

        if not args.sync:
            print("\n   Next: Sync the index to generate embeddings:")
            print("   uv run python scripts/load_documents.py --sync")
        else:
            print("\n   Index sync triggered. Wait a few minutes for embeddings.")

        print("\n   Test with:")
        print(
            "   uv run python -c \"from src.agents.rag_agent import RAGAgent; from src.config import Config; r = RAGAgent(Config.from_env()); print(r.query('What is the refund policy?').answer)\""
        )


if __name__ == "__main__":
    main()
