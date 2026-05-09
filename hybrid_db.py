import sqlite3
import socket
from pymongo import MongoClient
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HybridDB:
    def __init__(self, mongo_uri, db_name):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.online = False
        self.client = None
        self.mongo_db = None
        self.sqlite_conn = sqlite3.connect("local_cache.db", check_same_thread=False)
        self.sqlite_conn.row_factory = sqlite3.Row
        self._init_sqlite()
        self._check_connectivity()
        
        # Start background sync thread
        self.sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self.sync_thread.start()

    def _init_sqlite(self):
        cursor = self.sqlite_conn.cursor()
        
        # Projects Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Projects (
            project_id INTEGER PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            priority TEXT,
            signed TEXT,
            synced INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0
        )
        """)
        
        # TeamMembers Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamMembers (
            member_id INTEGER PRIMARY KEY,
            name TEXT,
            role TEXT,
            synced INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0
        )
        """)
        
        # Tasks Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tasks (
            task_id INTEGER PRIMARY KEY,
            project_id INTEGER,
            name TEXT,
            assigned_to INTEGER,
            status TEXT,
            due_date TEXT,
            comments TEXT,
            signed TEXT,
            synced INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0
        )
        """)
        
        # Targets Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Targets (
            target_id INTEGER PRIMARY KEY,
            project_id INTEGER,
            name TEXT,
            due_date TEXT,
            status TEXT,
            description TEXT,
            synced INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0
        )
        """)
        
        # Counters for manual sequences
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Counters (
            _id TEXT PRIMARY KEY,
            seq INTEGER
        )
        """)
        
        self.sqlite_conn.commit()

    def _check_connectivity(self):
        try:
            # Check internet by pinging a common server
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            
            if not self.client:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                self.mongo_db = self.client[self.db_name]
            
            # Ping MongoDB specifically
            self.client.admin.command('ping')
            
            if not self.online:
                logging.info("System is ONLINE. Connected to MongoDB Atlas.")
            self.online = True
        except Exception:
            if self.online:
                logging.warning("System is OFFLINE. Switching to local SQLite.")
            self.online = False

    def _auto_sync_loop(self):
        while True:
            time.sleep(15) # Check every 15 seconds
            self._check_connectivity()
            if self.online:
                try:
                    self.sync_to_cloud()
                    self.sync_from_cloud()
                except Exception as e:
                    logging.error(f"Sync error: {e}")

    def get_next_sequence(self, name):
        # Always try to get from cloud if possible to avoid ID collisions
        if self.online:
            try:
                ret = self.mongo_db["Counters"].find_one_and_update(
                    {"_id": name},
                    {"$inc": {"seq": 1}},
                    upsert=True,
                    return_document=True
                )
                seq = ret["seq"]
                # Update local counter too
                cursor = self.sqlite_conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO Counters (_id, seq) VALUES (?, ?)", (name, seq))
                self.sqlite_conn.commit()
                return seq
            except:
                pass
        
        # Fallback to local counter
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT seq FROM Counters WHERE _id=?", (name,))
        row = cursor.fetchone()
        if row:
            seq = row['seq'] + 1
            cursor.execute("UPDATE Counters SET seq=? WHERE _id=?", (seq, name))
        else:
            seq = 1
            cursor.execute("INSERT INTO Counters (_id, seq) VALUES (?, ?)", (name, seq))
        self.sqlite_conn.commit()
        return seq

    def sync_to_cloud(self):
        if not self.online: return
        cursor = self.sqlite_conn.cursor()
        
        tables = {
            "Projects": "project_id",
            "TeamMembers": "member_id",
            "Tasks": "task_id",
            "Targets": "target_id"
        }
        
        for table, pk in tables.items():
            # Handle Deletions first
            cursor.execute(f"SELECT {pk} FROM {table} WHERE is_deleted=1")
            for row in cursor.fetchall():
                self.mongo_db[table].delete_one({pk: row[0]})
                cursor.execute(f"DELETE FROM {table} WHERE {pk}=?", (row[0],))
            
            # Handle Inserts/Updates
            cursor.execute(f"SELECT * FROM {table} WHERE synced=0 AND is_deleted=0")
            columns = [column[0] for column in cursor.description]
            for row in cursor.fetchall():
                data = dict(row)
                del data['synced']
                del data['is_deleted']
                self.mongo_db[table].replace_one({pk: data[pk]}, data, upsert=True)
                cursor.execute(f"UPDATE {table} SET synced=1 WHERE {pk}=?", (data[pk],))
        
        self.sqlite_conn.commit()

    def sync_from_cloud(self):
        """Optionally pull new data from cloud to local cache"""
        if not self.online: return
        cursor = self.sqlite_conn.cursor()
        
        tables = {
            "Projects": "project_id",
            "TeamMembers": "member_id",
            "Tasks": "task_id",
            "Targets": "target_id"
        }
        
        for table, pk in tables.items():
            cloud_data = list(self.mongo_db[table].find())
            for item in cloud_data:
                if "_id" in item: del item["_id"]
                
                # Check if local has unsynced changes for this record
                cursor.execute(f"SELECT synced FROM {table} WHERE {pk}=?", (item[pk],))
                row = cursor.fetchone()
                if row and row['synced'] == 0:
                    continue # Don't overwrite unsynced local changes
                
                # Upsert into local
                cols = ", ".join(item.keys())
                placeholders = ", ".join(["?"] * len(item))
                cursor.execute(f"INSERT OR REPLACE INTO {table} ({cols}, synced) VALUES ({placeholders}, 1)", list(item.values()))
        
        self.sqlite_conn.commit()

    def insert_one(self, collection, data):
        pk_map = {"Projects": "project_id", "TeamMembers": "member_id", "Tasks": "task_id", "Targets": "target_id"}
        pk = pk_map.get(collection)
        
        if self.online:
            try:
                self.mongo_db[collection].insert_one(data.copy())
                # Also save to local
                self._local_upsert(collection, data, synced=1)
                return True
            except Exception as e:
                logging.error(f"Online insert failed: {e}")
                # Fallback to local
        
        self._local_upsert(collection, data, synced=0)
        return True

    def update_one(self, collection, filter_query, update_data):
        # Simplified: extract first key from filter and update
        # Project-Ace-1 uses simple filters like {'project_id': pid}
        pk_field = list(filter_query.keys())[0]
        pk_val = filter_query[pk_field]
        
        # update_data is usually {'$set': {...}}
        if '$set' in update_data:
            real_data = update_data['$set']
        else:
            real_data = update_data

        if self.online:
            try:
                self.mongo_db[collection].update_one(filter_query, update_data)
                # Update local
                self._local_update(collection, pk_field, pk_val, real_data, synced=1)
                return True
            except:
                pass
        
        self._local_update(collection, pk_field, pk_val, real_data, synced=0)
        return True

    def delete_one(self, collection, filter_query):
        pk_field = list(filter_query.keys())[0]
        pk_val = filter_query[pk_field]
        
        if self.online:
            try:
                self.mongo_db[collection].delete_one(filter_query)
                # Delete local
                cursor = self.sqlite_conn.cursor()
                cursor.execute(f"DELETE FROM {collection} WHERE {pk_field}=?", (pk_val,))
                self.sqlite_conn.commit()
                return True
            except:
                pass
        
        # Mark as deleted for sync later
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"UPDATE {collection} SET is_deleted=1 WHERE {pk_field}=?", (pk_val,))
        self.sqlite_conn.commit()
        return True

    def delete_many(self, collection, filter_query):
        # Handled specifically for cascade deletes in this app
        pk_field = list(filter_query.keys())[0]
        pk_val = filter_query[pk_field]
        
        if self.online:
            try:
                self.mongo_db[collection].delete_many(filter_query)
            except:
                pass
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"UPDATE {collection} SET is_deleted=1 WHERE {pk_field}=?", (pk_val,))
        self.sqlite_conn.commit()
        return True

    def update_many(self, collection, filter_query, update_data):
        # Handled specifically for set to None (AssignedTo)
        if self.online:
            try:
                self.mongo_db[collection].update_many(filter_query, update_data)
            except:
                pass
        
        pk_field = list(filter_query.keys())[0]
        pk_val = filter_query[pk_field]
        if '$set' in update_data:
            set_data = update_data['$set']
            col_name = list(set_data.keys())[0]
            val = set_data[col_name]
            cursor = self.sqlite_conn.cursor()
            cursor.execute(f"UPDATE {collection} SET {col_name}=?, synced=0 WHERE {pk_field}=?", (val, pk_val))
            self.sqlite_conn.commit()

    def find(self, collection, query=None, sort_by=None, ascending=True):
        if self.online:
            try:
                cursor = self.mongo_db[collection].find(query)
                if sort_by:
                    cursor = cursor.sort(sort_by, 1 if ascending else -1)
                data = list(cursor)
                for d in data: d.pop('_id', None)
                return data
            except:
                pass
        
        # Local find
        cursor = self.sqlite_conn.cursor()
        q = f"SELECT * FROM {collection} WHERE is_deleted=0"
        params = []
        if query:
            for k, v in query.items():
                q += f" AND {k}=?"
                params.append(v)
        
        if sort_by:
            q += f" ORDER BY {sort_by} {'ASC' if ascending else 'DESC'}"
        
        cursor.execute(q, params)
        return [dict(row) for row in cursor.fetchall()]

    def find_one(self, collection, query):
        if self.online:
            try:
                res = self.mongo_db[collection].find_one(query)
                if res: res.pop('_id', None)
                return res
            except:
                pass
        
        cursor = self.sqlite_conn.cursor()
        q = f"SELECT * FROM {collection} WHERE is_deleted=0"
        params = []
        for k, v in query.items():
            q += f" AND {k}=?"
            params.append(v)
        cursor.execute(q, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def count_documents(self, collection, query):
        if self.online:
            try:
                return self.mongo_db[collection].count_documents(query)
            except:
                pass
        
        cursor = self.sqlite_conn.cursor()
        q = f"SELECT COUNT(*) FROM {collection} WHERE is_deleted=0"
        params = []
        for k, v in query.items():
            q += f" AND {k}=?"
            params.append(v)
        cursor.execute(q, params)
        return cursor.fetchone()[0]

    def _local_upsert(self, collection, data, synced):
        cursor = self.sqlite_conn.cursor()
        cols = ", ".join(list(data.keys()) + ["synced", "is_deleted"])
        placeholders = ", ".join(["?"] * (len(data) + 2))
        vals = list(data.values()) + [synced, 0]
        cursor.execute(f"INSERT OR REPLACE INTO {collection} ({cols}) VALUES ({placeholders})", vals)
        self.sqlite_conn.commit()

    def _local_update(self, collection, pk_field, pk_val, real_data, synced):
        cursor = self.sqlite_conn.cursor()
        set_clause = ", ".join([f"{k}=?" for k in real_data.keys()]) + ", synced=?"
        vals = list(real_data.values()) + [synced, pk_val]
        cursor.execute(f"UPDATE {collection} SET {set_clause} WHERE {pk_field}=?", vals)
        self.sqlite_conn.commit()
