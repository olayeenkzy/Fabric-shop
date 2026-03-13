from flask import Flask, render_template, request, redirect, session, Response
import sqlite3
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE = "database.db"


def get_db():
    return sqlite3.connect(DATABASE)


def init_db():

    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS fabrics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        cost REAL,
        price REAL,
        quantity INTEGER
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fabric_id INTEGER,
        qty INTEGER,
        total REAL,
        profit REAL,
        date TEXT
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    admin = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()

    if not admin:
        db.execute("INSERT INTO users(username,password,role) VALUES('admin','admin123','admin')")

    db.commit()


init_db()

@app.route("/ping")
def ping():
    return "alive"

@app.route("/health")
def health():
    return {"status": "running"}

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if user:
            session["user"] = username
            session["role"] = user[3]
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    db = get_db()

    fabrics = db.execute("SELECT * FROM fabrics").fetchall()

    revenue = db.execute("SELECT SUM(total) FROM sales").fetchone()[0]
    profit = db.execute("SELECT SUM(profit) FROM sales").fetchone()[0]

    revenue = revenue if revenue else 0
    profit = profit if profit else 0

    return render_template(
        "dashboard.html",
        fabrics=fabrics,
        revenue=revenue,
        profit=profit,
        role=session["role"]
    )


@app.route("/add_fabric", methods=["GET", "POST"])
def add_fabric():

    if request.method == "POST":

        name = request.form["name"]
        cost = float(request.form["cost"])
        price = float(request.form["price"])
        qty = int(request.form["qty"])

        db = get_db()

        db.execute(
            "INSERT INTO fabrics(name,cost,price,quantity) VALUES(?,?,?,?)",
            (name, cost, price, qty)
        )

        db.commit()

        return redirect("/dashboard")

    return render_template("add_fabric.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_fabric(id):

    if session["role"] != "admin":
        return redirect("/dashboard")

    db = get_db()

    fabric = db.execute("SELECT * FROM fabrics WHERE id=?", (id,)).fetchone()

    if request.method == "POST":

        cost = float(request.form["cost"])
        price = float(request.form["price"])

        db.execute(
            "UPDATE fabrics SET cost=?, price=? WHERE id=?",
            (cost, price, id)
        )

        db.commit()

        return redirect("/dashboard")

    return render_template("edit.html", fabric=fabric)


# 🔽 PASTE THIS DIRECTLY BELOW THE EDIT FUNCTION

@app.route("/settings", methods=["GET","POST"])
def settings():

    if session["role"] != "admin":
        return redirect("/dashboard")

    db = get_db()

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db.execute(
            "UPDATE users SET username=?, password=? WHERE role='admin'",
            (username,password)
        )

        db.commit()

        return redirect("/dashboard")

    user = db.execute("SELECT * FROM users WHERE role='admin'").fetchone()

    return render_template("settings.html", user=user)
@app.route("/delete/<int:id>")
def delete_fabric(id):

    if session["role"] != "admin":
        return redirect("/dashboard")

    db = get_db()

    db.execute("DELETE FROM fabrics WHERE id=?", (id,))
    db.commit()

    return redirect("/dashboard")


@app.route("/reset/<int:id>")
def reset_stock(id):

    if session["role"] != "admin":
        return redirect("/dashboard")

    db = get_db()

    db.execute("UPDATE fabrics SET quantity=0 WHERE id=?", (id,))
    db.commit()

    return redirect("/dashboard")


@app.route("/record_sale/<int:id>", methods=["GET", "POST"])
def record_sale(id):

    db = get_db()

    fabric = db.execute("SELECT * FROM fabrics WHERE id=?", (id,)).fetchone()

    if request.method == "POST":

        qty = int(request.form["qty"])

        total = qty * fabric[3]
        profit = qty * (fabric[3] - fabric[2])

        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        db.execute(
            "INSERT INTO sales(fabric_id,qty,total,profit,date) VALUES(?,?,?,?,?)",
            (id, qty, total, profit, date)
        )

        db.execute(
            "UPDATE fabrics SET quantity = quantity - ? WHERE id=?",
            (qty, id)
        )

        db.commit()

        return render_template(
            "receipt.html",
            fabric=fabric,
            qty=qty,
            total=total,
            date=date
        )

    return render_template("record_sale.html", fabric=fabric)


@app.route("/sales_history")
def sales_history():

    db = get_db()

    sales = db.execute(
        """
        SELECT sales.id, fabrics.name, sales.qty, sales.total, sales.profit, sales.date
        FROM sales
        JOIN fabrics ON sales.fabric_id=fabrics.id
        ORDER BY sales.id DESC
        """
    ).fetchall()

    return render_template("sales.html", sales=sales)


@app.route("/delete_sale/<int:id>")
def delete_sale(id):

    if session.get("role") != "admin":
        return redirect("/dashboard")

    db = get_db()

    db.execute("DELETE FROM sales WHERE id=?", (id,))
    db.commit()

    return redirect("/sales_history")

@app.route("/reset_sales")
def reset_sales():

    if session.get("role") != "admin":
        return redirect("/dashboard")

    db = get_db()

    db.execute("DELETE FROM sales")

    db.commit()

    return redirect("/dashboard")
@app.route("/export_csv")
def export_csv():

    db = get_db()

    sales = db.execute(
        """
        SELECT fabrics.name, sales.qty, sales.total, sales.profit, sales.date
        FROM sales
        JOIN fabrics ON sales.fabric_id=fabrics.id
        """
    ).fetchall()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(["Fabric", "Quantity", "Total", "Profit", "Date"])

    for row in sales:
        writer.writerow(row)

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sales.csv"}
    )

    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)