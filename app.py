import os
import sqlite3
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename


# Ensure 'uploads' folder exists to store database and files
os.makedirs('uploads', exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

DB_PATH = os.path.join('uploads', 'tickets.db')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT,
                dashboard TEXT,
                stream TEXT,
                raised_by TEXT,
                subject TEXT,
                date_logged TEXT,
                closed_date TEXT,
                priority TEXT,
                status TEXT,
                assigned_to TEXT,
                description TEXT,
                attachment TEXT
            )
        ''')
        conn.commit()
        conn.close()

@app.route("/")
def home():
    return render_template("rafey.html")

@app.route("/add_ticket", methods=["POST"])
def add_ticket():
    try:
        data = request.form
        file = request.files.get('attachment')
        attachment = None

        if file and file.filename and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            attachment = filename

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO tickets (
                dashboard, stream, raised_by, subject, date_logged, closed_date,
                priority, status, assigned_to, description, attachment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('dashboard'), data.get('stream'), data.get('raised_by'),
            data.get('subject'), data.get('date_logged'), data.get('closed_date'),
            data.get('priority'), data.get('status'), data.get('assigned_to'),
            data.get('description'), attachment
        ))

        ticket_id = cur.lastrowid
        ticket_no = f"ARM-{ticket_id:03d}"
        cur.execute('UPDATE tickets SET ticket_no=? WHERE id=?', (ticket_no, ticket_id))
        conn.commit()
        conn.close()

        return jsonify({"message": "Ticket added successfully", "ticket_no": ticket_no}), 200

    except Exception as e:
        print(f"❌ Error adding ticket: {e}")
        return jsonify({"error": "Failed to add ticket"}), 500

@app.route("/update_ticket", methods=["POST"])
def update_ticket():
    try:
        data = request.form
        ticket_id = data.get('id')
        if not ticket_id:
            return jsonify({"error": "Missing ticket ID"}), 400

        file = request.files.get('attachment')
        attachment = None

        if file and file.filename and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            attachment = filename

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if attachment:
            cur.execute('''
                UPDATE tickets SET
                    dashboard=?, ticket_no=?, stream=?, raised_by=?, subject=?,
                    date_logged=?, closed_date=?, priority=?, status=?, assigned_to=?,
                    description=?, attachment=?
                WHERE id=?
            ''', (
                data.get('dashboard'), data.get('ticket_no'), data.get('stream'),
                data.get('raised_by'), data.get('subject'), data.get('date_logged'),
                data.get('closed_date'), data.get('priority'), data.get('status'),
                data.get('assigned_to'), data.get('description'), attachment, ticket_id
            ))
        else:
            cur.execute('''
                UPDATE tickets SET
                    dashboard=?, ticket_no=?, stream=?, raised_by=?, subject=?,
                    date_logged=?, closed_date=?, priority=?, status=?, assigned_to=?,
                    description=?
                WHERE id=?
            ''', (
                data.get('dashboard'), data.get('ticket_no'), data.get('stream'),
                data.get('raised_by'), data.get('subject'), data.get('date_logged'),
                data.get('closed_date'), data.get('priority'), data.get('status'),
                data.get('assigned_to'), data.get('description'), ticket_id
            ))

        conn.commit()
        conn.close()
        return jsonify({"message": "Ticket updated successfully"}), 200

    except Exception as e:
        print(f"❌ Error updating ticket: {e}")
        return jsonify({"error": "Failed to update ticket"}), 500

@app.route("/get_tickets")
def get_tickets():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            SELECT id, dashboard, ticket_no, stream, raised_by, subject, date_logged,
            closed_date, priority, status, assigned_to, description, attachment
            FROM tickets ORDER BY 
                CASE status
                    WHEN 'Open' THEN 1
                    WHEN 'In Progress' THEN 2
                    WHEN 'Closed' THEN 3
                    ELSE 4
                END,
                id DESC
        ''')
        rows = cur.fetchall()
        conn.close()

        tickets = []
        for row in rows:
            attachment_url = url_for('uploaded_file', filename=row[12]) if row[12] else None
            tickets.append({
                "id": row[0], "dashboard": row[1], "ticket_no": row[2],
                "stream": row[3], "raised_by": row[4], "subject": row[5],
                "date_logged": row[6], "closed_date": row[7],
                "priority": row[8], "status": row[9], "assigned_to": row[10],
                "description": row[11], "attachment": attachment_url
            })

        return jsonify(tickets)
    except Exception as e:
        print(f"❌ Error fetching tickets: {e}")
        return jsonify([])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/delete_ticket", methods=["POST"])
def delete_ticket():
    data = request.json
    if not data or "id" not in data:
        return jsonify({"error": "Missing ticket ID"}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM tickets WHERE id = ?", (data["id"],))
        conn.commit()
        conn.close()
        return jsonify({"message": "Ticket deleted successfully"}), 200
    except Exception as e:
        print(f"❌ Error deleting ticket: {e}")
        return jsonify({"error": "Failed to delete ticket"}), 500

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
