import os
from typing import Optional

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

_CONN: Optional[mysql.connector.MySQLConnection] = None


def _dsn() -> dict:
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    if not user or not password:
        raise RuntimeError("MYSQL_USER and MYSQL_PASSWORD must be set")
    return {
        "host": f"{user}.mysql.pythonanywhere-services.com",
        "user": user,
        "passwd": password,
        "database": f"{user}$default",
        "autocommit": False,
    }


def get_connection() -> mysql.connector.MySQLConnection:
    global _CONN
    if _CONN is None or not _CONN.is_connected():
        _CONN = mysql.connector.connect(**_dsn())
    return _CONN


def ensure_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title TEXT,
            content MEDIUMTEXT,
            aicontent MEDIUMTEXT,
            summary MEDIUMTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestrator_tasks (
            task_id VARCHAR(128) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            owner VARCHAR(64),
            status VARCHAR(32) NOT NULL DEFAULT 'queued',
            priority VARCHAR(16) NOT NULL DEFAULT 'normal',
            acceptance TEXT,
            details_json JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestrator_events (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(128),
            actor VARCHAR(64) NOT NULL,
            perspective VARCHAR(32) DEFAULT 'executor',
            kind VARCHAR(32) NOT NULL,
            status VARCHAR(32),
            summary TEXT NOT NULL,
            details_json JSON,
            refs_json JSON,
            dedupe_key VARCHAR(255),
            source VARCHAR(32) DEFAULT 'agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_orch_dedupe (dedupe_key),
            INDEX idx_orch_task (task_id),
            INDEX idx_orch_actor (actor),
            INDEX idx_orch_kind (kind),
            CONSTRAINT fk_orch_task
              FOREIGN KEY (task_id) REFERENCES orchestrator_tasks(task_id)
              ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    conn.commit()
    cur.close()
