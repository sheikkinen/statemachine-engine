"""
Database Base Class

Generic SQLite database connection manager for state machine engine.
Loads schemas from configurable directories.

IMPORTANT: Changes via Change Management, see CLAUDE.md
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    """SQLite database manager for state machine engine"""

    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.schema_dir = Path(__file__).parent.parent / "schema"
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute_schema_file(self, schema_file: Path):
        """Execute SQL from schema file"""
        logger.debug(f"Loading schema from {schema_file.name}")
        with self._get_connection() as conn:
            sql = schema_file.read_text()
            conn.executescript(sql)
            conn.commit()

    def _ensure_tables(self):
        """Create database tables by loading schema files"""
        # Load generic tables (engine-ready)
        generic_dir = self.schema_dir / "generic"
        if generic_dir.exists():
            for schema_file in sorted(generic_dir.glob("*.sql")):
                self._execute_schema_file(schema_file)

        # Load domain-specific tables (face-changer)
        domain_dir = self.schema_dir / "domain"
        if domain_dir.exists():
            for schema_file in sorted(domain_dir.glob("*.sql")):
                self._execute_schema_file(schema_file)
