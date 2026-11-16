import os, sqlite3
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
API_KEY = "ALPHA-8305-KEY"  # admin website me bhi yahi key rakhni hai
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "applications.db")


def make_ranks():
    ranks = ["Unranked"]
    for tier, n in [("Bronze", 3), ("Silver", 3), ("Gold", 4), ("Platinum", 4), ("Diamond", 4)]:
        for i in range(n):
            ranks.append(f"{tier} {['I', 'II', 'III', 'IV'][i]}")
    return ranks + ["Heroic", "Elite Heroic", "Master", "Grandmaster"]


RANKS = make_ranks()
PRIME = list(range(0, 9))
GAMEPLAY = ["Noob", "Pro", "Legend"]
AGES = list(range(10, 41))


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init_db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, old_guild TEXT, level TEXT,
        cs_rank TEXT, br_rank TEXT, prime TEXT, gameplay TEXT, age TEXT,
        status TEXT DEFAULT 'Pending', note TEXT DEFAULT '',
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.commit()
    c.close()


init_db()


def form_no(i):
    return f"TA-{1000 + i}"


@app.route("/", methods=["GET", "POST"])
def apply():
    error = None
    if request.method == "POST":
        f = request.form
        uid, level = f.get("uid", "").strip(), f.get("level", "").strip()
        if not uid.isdigit() or not level.isdigit():
            error = "UID and Level must be numbers."
        elif f.get("cs_rank") not in RANKS or f.get("br_rank") not in RANKS \
                or f.get("prime") not in map(str, PRIME) or f.get("gameplay") not in GAMEPLAY \
                or f.get("age") not in map(str, AGES):
            error = "Please choose all options."
        if not error:
            cur = db().execute(
                "INSERT INTO applications (uid, old_guild, level, cs_rank, br_rank, prime, gameplay, age) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (uid, f.get("old_guild", "").strip(), level, f["cs_rank"], f["br_rank"],
                 f["prime"], f["gameplay"], f["age"]))
            db().commit()
            return render_template("done.html", number=form_no(cur.lastrowid))
    return render_template("apply.html", ranks=RANKS, prime=PRIME, gameplay=GAMEPLAY,
                           ages=AGES, error=error)


@app.route("/status", methods=["GET", "POST"])
def status():
    row, searched = None, False
    if request.method == "POST":
        searched = True
        raw = request.form.get("number", "").strip().upper().replace("TA-", "")
        if raw.isdigit():
            row = db().execute("SELECT * FROM applications WHERE id=?", (int(raw) - 1000,)).fetchone()
    return render_template("status.html", row=row, searched=searched,
                           number=request.form.get("number", ""))


# ---------- API (admin website will use this later) ----------
def api_ok():
    return request.headers.get("X-API-Key") == API_KEY


@app.route("/api/applications")
def api_list():
    if not api_ok():
        return jsonify(error="unauthorized"), 401
    rows = db().execute(
        "SELECT * FROM applications ORDER BY (status='Pending') DESC, id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["form_no"] = form_no(r["id"])
        out.append(d)
    return jsonify(out)


@app.route("/api/decide/<int:i>", methods=["POST"])
def api_decide(i):
    if not api_ok():
        return jsonify(error="unauthorized"), 401
    data = request.get_json(force=True)
    if data.get("status") not in ("Accepted", "Rejected"):
        return jsonify(error="bad status"), 400
    db().execute("UPDATE applications SET status=?, note=? WHERE id=?",
                 (data["status"], data.get("note", "").strip(), i))
    db().commit()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
