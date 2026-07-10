from __future__ import annotations

import json
import sqlite3

from lethe.core.block import Block, BlockState
from lethe.stores.base import Note


class SqliteStore:
    def __init__(self, path: str = "./lethe.db"):
        # check_same_thread=False: the MCP server serves tools from a threadpool,
        # so the connection must be usable across threads.
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS blocks(
            id TEXT PRIMARY KEY, session TEXT, role TEXT, kind TEXT, content TEXT,
            created_step INT, pinned INT, tokens INT, state TEXT, handle TEXT, meta TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS notes(
            id TEXT PRIMARY KEY, session TEXT, summary TEXT, covers TEXT, tokens INT)""")
        self.db.execute("CREATE TABLE IF NOT EXISTS refs(src TEXT, dst TEXT)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            ts TEXT, session TEXT, kind TEXT, payload TEXT)""")
        self.db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts
            USING fts5(id UNINDEXED, content)""")
        self.db.commit()

    def put(self, block: Block) -> None:
        self.db.execute("REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            block.id, block.meta.get("session", ""), block.role, block.kind, block.content,
            block.created_step, int(block.pinned), block.tokens,
            block.state.value, block.handle, json.dumps(block.meta)))
        self.db.execute("DELETE FROM blocks_fts WHERE id=?", (block.id,))
        self.db.execute("INSERT INTO blocks_fts(id, content) VALUES (?,?)",
                        (block.id, block.content))
        # persist the citation graph (src cites dst), replacing this block's edges
        self.db.execute("DELETE FROM refs WHERE src=?", (block.id,))
        self.db.executemany("INSERT INTO refs VALUES (?,?)",
                            [(block.id, dst) for dst in block.refs])
        self.db.commit()

    def _row_to_block(self, row) -> Block:
        return Block(id=row[0], role=row[2], kind=row[3], content=row[4],
                     created_step=row[5], pinned=bool(row[6]), tokens=row[7],
                     state=BlockState(row[8]), handle=row[9],
                     meta=json.loads(row[10] or "{}"))

    def get(self, handle: str) -> Block | None:
        cur = self.db.execute("SELECT * FROM blocks WHERE handle=?", (handle,))
        row = cur.fetchone()
        return self._row_to_block(row) if row else None

    def search(self, query: str, limit: int) -> list[Block]:
        q = query.strip()
        if not q:
            return []
        # Quote the whole query as one FTS5 phrase so arbitrary model text —
        # colons, quotes, AND/OR/NEAR, wildcards — is treated as literal terms
        # and never parsed as FTS syntax (which would raise OperationalError).
        phrase = '"' + q.replace('"', '""') + '"'
        try:
            cur = self.db.execute(
                "SELECT b.* FROM blocks_fts f JOIN blocks b ON b.id=f.id "
                "WHERE blocks_fts MATCH ? LIMIT ?", (phrase, limit))
            return [self._row_to_block(r) for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    def refs_of(self, src: str) -> list[str]:
        cur = self.db.execute("SELECT dst FROM refs WHERE src=?", (src,))
        return [r[0] for r in cur.fetchall()]

    def put_note(self, note: Note) -> None:
        self.db.execute("REPLACE INTO notes VALUES (?,?,?,?,?)",
            (note.id, note.session, note.summary, json.dumps(note.covers), note.tokens))
        self.db.commit()

    def events(self, kind: str, payload: dict) -> None:
        self.db.execute("INSERT INTO events VALUES (datetime('now'), ?, ?, ?)",
                        (payload.get("session", ""), kind, json.dumps(payload)))
        self.db.commit()
