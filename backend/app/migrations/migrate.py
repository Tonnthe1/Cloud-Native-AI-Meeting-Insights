#!/usr/bin/env python3
"""
Database migration runner for Meeting Insights
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all SQL migration files in order."""
    
    engine = create_engine(DATABASE_URL)
    migrations_dir = Path(__file__).parent
    
    # Get all SQL files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.info("No migration files found")
        return
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    with engine.connect() as conn:
        # Create migrations tracking table if it doesn't exist
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_history (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        
        for migration_file in migration_files:
            filename = migration_file.name
            
            # Check if migration already applied
            result = conn.execute(
                text("SELECT filename FROM migration_history WHERE filename = :filename"),
                {"filename": filename}
            )
            
            if result.fetchone():
                logger.info(f"Migration {filename} already applied, skipping")
                continue
            
            logger.info(f"Applying migration: {filename}")
            
            try:
                # Read and execute migration
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                
                # Execute migration
                conn.execute(text(migration_sql))
                
                # Record migration as applied
                conn.execute(
                    text("INSERT INTO migration_history (filename) VALUES (:filename)"),
                    {"filename": filename}
                )
                
                conn.commit()
                logger.info(f"Successfully applied migration: {filename}")
                
            except Exception as e:
                logger.error(f"Failed to apply migration {filename}: {e}")
                conn.rollback()
                raise

if __name__ == "__main__":
    run_migrations()