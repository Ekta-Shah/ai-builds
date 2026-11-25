"""Run model-written SQL for one user without trusting the SQL.
Isolation is enforced here, in code: the database is opened read-only, the user only sees temp views
filtered to their stores, and an authorizer blocks everything else. A prompt cannot talk its way past this."""
import os, sqlite3, time

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "retail.db")
BASE = {"sales", "stores", "products"}
MAX_ROWS = 50
TIMEOUT_S = 5


class Blocked(Exception):
    pass


def connect(stores):
    con = sqlite3.connect(f"file:{os.path.abspath(DB)}?mode=ro", uri=True, check_same_thread=False)
    ids = ",".join("'" + s + "'" for s in stores)
    con.execute(f"CREATE TEMP VIEW sales AS SELECT * FROM main.sales WHERE store_id IN ({ids})")
    con.execute(f"CREATE TEMP VIEW stores AS SELECT * FROM main.stores WHERE store_id IN ({ids})")
    con.execute("CREATE TEMP VIEW products AS SELECT * FROM main.products")

    def auth(action, a1, a2, a3, a4):
        if action in (21, 31, 33):          # SELECT, FUNCTION, RECURSIVE
            return sqlite3.SQLITE_OK
        if action == 20:                    # READ a column: only through the scoped views
            if a1 in BASE and a4 is None and a3 == "main":
                return sqlite3.SQLITE_DENY  # direct hit on a base table
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY          # no writes, ATTACH, PRAGMA, anything else

    con.set_authorizer(auth)
    return con


def run(stores, sql):
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        raise Blocked("one statement only")
    if not sql.lower().startswith(("select", "with")):
        raise Blocked("select only")
    con = connect(stores)
    t0 = time.time()
    con.set_progress_handler(lambda: 1 if time.time() - t0 > TIMEOUT_S else 0, 10000)
    try:
        cur = con.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchmany(MAX_ROWS)
    except sqlite3.DatabaseError as e:
        raise Blocked(str(e))
    finally:
        con.close()
    return cols, rows


if __name__ == "__main__":
    import json
    users = json.load(open(os.path.join(os.path.dirname(__file__), "..", "users.json")))
    for who, sql in [("ana", "select store_id, count(*) from sales group by 1"),
                     ("ana", "select * from main.sales limit 1"),
                     ("meera", "select store_id, count(*) from sales group by 1"),
                     ("ana", "drop table sales"),
                     ("ana", "select 1; select 2")]:
        try:
            print(who, run(users[who]["stores"], sql))
        except Blocked as e:
            print(who, "BLOCKED:", e)
