# coding: utf-8
# Copyright 2012 litl, LLC. All Rights Reserved.

__version__ = "1.0.0"

import abc
import itertools
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

__all__ = ["SqliteStore", "KVStore"]


class KVStore(object):
    """An abstract key-value interface with support for range iteration."""
    __metaclass__ = abc.ABCMeta

    # Implement the Python context manager protocol.
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        """Release any resources associated with a KVStore.

        This is used to support the Python context manager protocol
        with semantics similar to ``contextlib.closing()``. That means
        you can use any concrete implementation of KVStore like:

        ::

            with park.SqliteStore("/path/to/db") as kv:
                kv.put("my_key", "my_value")

        """
        # Typically overridden by subclasses, this default
        # implementation does nothing.
        pass

    def contains(self, key):
        """True if the store contains key."""
        return self.get(key, default=None) is not None

    @abc.abstractmethod
    def get(self, key, default=None):  # pragma: no cover
        """Get the value associated with a key.

        :param key: The key to retrieve.
        :type key: bytes

        :param default: A default value to return if the key is not
            present in the store.

        :returns: The value associated with ``key``.

        """
        pass

    @abc.abstractmethod
    def put(self, key, value):  # pragma: no cover
        """Put a key-value pair into the store.

        If the key is already present, this replaces its value. Both
        the key and value are binary safe.

        :param key: The key to set.
        :type key: bytes

        :param value: The value to set the key to.
        :type value: bytes

        """
        pass

    @abc.abstractmethod
    def put_many(self, items):  # pragma: no cover
        """Put many key-value pairs.

        This method may take advantage of performance or atomicity
        features of the underlying store. It does not guarantee that
        all items will be set in the same transaction, only that
        transactions may be used for performance.

        :param items: An iterable producing (key, value) tuples.

        """
        for key, value in items:
            self.put(key, value)

    @abc.abstractmethod
    def delete(self, key):  # pragma: no cover
        """Remove a key from the store.

        :param key: The key to remove.
        :type key: bytes

        """
        pass

    @abc.abstractmethod
    def delete_many(self, keys):  # pragma: no cover
        """Remove many keys from the store.

        :param keys: An iterable producing keys to remove.

        """
        for key in keys:
            self.delete(key)

    @abc.abstractmethod
    def keys(self, key_from=None, key_to=None):  # pragma: no cover
        """Get a lexically sorted range of keys.

        :param key_from: Lower bound (inclusive), or None for unbounded.
        :type key_from: bytes

        :param key_to: Upper bound (inclusive), or None for unbounded.
        :type key_to: bytes

        :yields: All keys from the store where ``key_from <= key <= key_to``.

        """
        pass

    @abc.abstractmethod
    def items(self, key_from=None, key_to=None):  # pragma: no cover
        """Get a lexically sorted range of (key, value) tuples.

        :param key_from: Lower bound (inclusive), or None for unbounded.
        :type key_from: bytes

        :param key_to: Upper bound (inclusive), or None for unbounded.
        :type key_to: bytes

        :yields: All (key, value) pairs from the store where
            ``key_from <= key <= key_to``.

        """
        pass

    def prefix_items(self, prefix, strip_prefix=False):
        """Get all (key, value) pairs with keys that begin with ``prefix``.

        :param prefix: Lexical prefix for keys to search.
        :type prefix: bytes

        :param strip_prefix: True to strip the prefix from yielded items.
        :type strip_prefix: bool

        :yields: All (key, value) pairs in the store where the keys
            begin with the ``prefix``.

        """
        items = self.items(key_from=prefix)

        start = 0
        if strip_prefix:
            start = len(prefix)

        for key, value in items:
            if not key.startswith(prefix):
                break
            yield key[start:], value

    def prefix_keys(self, prefix, strip_prefix=False):
        """Get all keys that begin with ``prefix``.

        :param prefix: Lexical prefix for keys to search.
        :type prefix: bytes

        :param strip_prefix: True to strip the prefix from yielded items.
        :type strip_prefix: bool

        :yields: All keys in the store that begin with ``prefix``.

        """
        keys = self.keys(key_from=prefix)

        start = 0
        if strip_prefix:
            start = len(prefix)

        for key in keys:
            if not key.startswith(prefix):
                break
            yield key[start:]


def ibatch(iterable, size):
    """Yield a series of batches from iterable, each size elements long."""
    source = iter(iterable)
    while True:
        batch = itertools.islice(source, size)
        yield itertools.chain([next(batch)], batch)


class SqliteStore(KVStore):
    """An implementation of KVStore in an SQLite database.

    :param path: The filesystem path for the database, which will be
        created if it doesn't exist.
    :type path: str

    This is what you want to use. See `KVStore` for what you can do
    with it.

    SqliteStore uses an embarrassingly simple SQL schema:

    .. code-block:: sql

        CREATE TABLE kv (
            key BLOB NOT NULL PRIMARY KEY,
            value BLOB NOT NULL)

    There are a few implications of this schema you might need to be
    aware of.

    1. Declaring ``key`` as PRIMARY KEY automatically indexes it,
       which gives constant time ordered traversal of keys and O(log
       n) lookup. However, SQLite 3 indexes the keys separately from
       the table data, which means your keys are effectively stored
       twice in the database. A primary key also means the index can't
       be dropped during bulk inserts.

    2. Using BLOBs for both columns keeps them binary safe, but it
       means everything going in must be type ``bytes``. Python
       ``str`` strings are converted automatically, but if you're
       dealing with Unicode data you'll need to encode it to bytes
       first. UTF-8 is a fine option:

    ::

        >>> kv.put("key", value.encode("utf-8"))
        >>> kv.get("key").decode("utf-8")

    """
    def __init__(self, path):
        need_schema = not os.path.exists(path)

        self.conn = sqlite3.connect(path)

        # Don't create unicode objects for retrieved values
        self.conn.text_factory = buffer

        # Disable the SQLite cache. Its pages tend to get swapped
        # out, even if the database file is in buffer cache.
        c = self.conn.cursor()
        c.execute("PRAGMA cache_size=0")
        c.execute("PRAGMA page_size=4096")

        # Use write-ahead logging if it's available, otherwise truncate
        journal_mode, = c.execute("PRAGMA journal_mode=WAL").fetchone()
        if journal_mode != "wal":
            c.execute("PRAGMA journal_mode=truncate")

        # Speed-for-reliability tradeoffs
        c.execute("PRAGMA temp_store=memory")
        c.execute("PRAGMA synchronous=OFF")

        if need_schema:
            self._create_db(self.conn)

    def close(self):
        self.conn.commit()
        self.conn.close()
        del self.conn

    def _create_db(self, conn):
        logger.debug("Creating SqliteStore schema")
        c = conn.cursor()

        c.execute("""
CREATE TABLE kv (
    key BLOB NOT NULL PRIMARY KEY,
    value BLOB NOT NULL)""")

        conn.commit()

    def get(self, key, default=None):
        q = "SELECT value FROM kv WHERE key = ?"
        c = self.conn.cursor()

        row = c.execute(q, (sqlite3.Binary(key),)).fetchone()
        if not row:
            return default

        return bytes(row[0])

    def put(self, key, value):
        q = "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)"
        self.conn.execute(q, (sqlite3.Binary(key), sqlite3.Binary(value)))
        self.conn.commit()

    def put_many(self, items):
        q = "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)"
        c = self.conn.cursor()

        blob = sqlite3.Binary
        for batch in ibatch(items, 30000):
            items = ((blob(key), blob(value)) for key, value in batch)

            c.executemany(q, items)
            self.conn.commit()

    def delete(self, key):
        q = "DELETE FROM kv WHERE key = ?"
        self.conn.execute(q, (sqlite3.Binary(key),))
        self.conn.commit()

    def delete_many(self, keys):
        q = "DELETE FROM kv WHERE key = ?"
        c = self.conn.cursor()

        blob = sqlite3.Binary
        for batch in ibatch(keys, 30000):
            items = ((blob(key),) for key in batch)

            c.executemany(q, items)
            self.conn.commit()

    def _range_where(self, key_from=None, key_to=None):
        if key_from is not None and key_to is None:
            return "WHERE key >= :key_from"

        if key_from is None and key_to is not None:
            return "WHERE key <= :key_to"

        if key_from is not None and key_to is not None:
            return "WHERE key BETWEEN :key_from AND :key_to"

        return ""

    def items(self, key_from=None, key_to=None):
        q = "SELECT key, value FROM kv %s ORDER BY key " \
            % self._range_where(key_from, key_to)

        if key_from is not None:
            key_from = sqlite3.Binary(key_from)

        if key_to is not None:
            key_to = sqlite3.Binary(key_to)

        c = self.conn.cursor()
        for key, value in c.execute(q, dict(key_from=key_from, key_to=key_to)):
            yield bytes(key), bytes(value)

    def keys(self, key_from=None, key_to=None):
        q = "SELECT key FROM kv %s ORDER BY key " \
            % self._range_where(key_from, key_to)

        if key_from is not None:
            key_from = sqlite3.Binary(key_from)

        if key_to is not None:
            key_to = sqlite3.Binary(key_to)

        c = self.conn.cursor()
        for key, in c.execute(q, dict(key_from=key_from, key_to=key_to)):
            yield bytes(key)
