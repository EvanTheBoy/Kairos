# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import sqlite3
from langchain_core.tools import tool

class PreferenceStore:
    def __init__(self, db_path="kairos.db"):
        self.db_path = db_path
        self._conn = None

    def _connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._create_table()
        return self._conn

    def _create_table(self):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
        conn.commit()

    def set(self, key: str, value: str):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

    def get(self, key: str) -> str | None:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

# Instantiate the store
preference_store = PreferenceStore()

@tool
def set_preference(key: str, value: str) -> str:
    """
    Sets a preference in the store. Use this to remember user choices or settings.
    """
    preference_store.set(key, value)
    return f"Preference '{key}' set successfully."

@tool
def get_preference(key: str) -> str:
    """
    Gets a preference from the store. Use this to recall user choices or settings.
    """
    value = preference_store.get(key)
    if value is None:
        return f"Preference '{key}' not found."
    return f"Preference '{key}' is '{value}'."
