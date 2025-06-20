import os
import uuid
import pyodbc
import logging
import traceback

from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Logging
logging.basicConfig(level=logging.DEBUG)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt', 'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

# SQL Server connection
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=saaitserver1.database.windows.net;'
    'DATABASE=SAAIT_Ticketing;'
    'UID=saait;'
    'PWD=sql@admin123;'
)

# Ensure tickets table exists
def init_db():
    cur = conn.cursor()
    cur.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='tickets' AND xtype='U')
        BEGIN
            CREATE TABLE tickets (
                id INT IDENTITY(1,1) PRIMARY KEY,
                Ticket_No VARCHAR(20),
                Dashboard VARCHAR(100),
                Stream VARCHAR(100),
                Raised_by VARCHAR(100),
                Subject VARCHAR(200),
                Date_logged VARCHAR(50),
                Closed_date VARCHAR(50),
                Priority VARCHAR(50),
                Status VARCHAR(50),
                Assigned_to VARCHAR(100),
                Description TEXT,
                Attachment VARCHAR(255)
            )
        END
    ''')
    conn.commit()
    cur.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HTML Pages
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/rafey.html")
def rafey_page():
    return render_template("rafey.html")

# Add Ticket
@app.route("/add_ticket", methods=["POST"])
def add_ticket():
    try:
        data = request.form
        file = request.files.get('attachment')
        attachment = None

        if file and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            attachment = filename

        cur = conn.cursor()
        cur.execute('''
            INSERT INTO tickets (
                dashboard, stream, raised_by, subject, date_logged, closed_date,
                priority, status, assigned_to, description, attachment
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('dashboard'), data.get('stream'), data.get('raised_by'),
            data.get('subject'), data.get('date_logged'), data.get('closed_date'),
            data.get('priority'), data.get('status'), data.get('assigned_to'),
            data.get('description'), attachment
        ))

        result = cur.fetchone()
        ticket_id = result[0] if result else None

        if ticket_id is None:
            return jsonify({"error": "Failed to retrieve ticket ID"}), 500

        ticket_no = f"ARM-{int(ticket_id):03d}"
        cur.execute('UPDATE tickets SET ticket_no=? WHERE id=?', (ticket_no, ticket_id))
        conn.commit()
        cur.close()

        return jsonify({"message": "Ticket added successfully", "ticket_no": ticket_no}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Update Ticket
@app.route("/update_ticket", methods=["POST"])
def update_ticket():
    try:
        data = request.form
        ticket_id = data.get('id')

        if not ticket_id:
            return jsonify({"error": "Missing ticket ID"}), 400

        ticket_id = int(ticket_id)
        file = request.files.get('attachment')
        attachment = None

        if file and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            attachment = filename

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
        cur.close()
        return jsonify({"message": "Ticket updated successfully"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to update ticket"}), 500

# Get Tickets
@app.route("/get_tickets")
def get_tickets():
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, dashboard, ticket_no, stream, raised_by, subject, date_logged,
                   closed_date, priority, status, assigned_to, description, attachment
            FROM tickets
            ORDER BY 
                CASE status
                    WHEN 'Open' THEN 1
                    WHEN 'In Progress' THEN 2
                    WHEN 'Closed' THEN 3
                    ELSE 4
                END, id DESC
        ''')
        rows = cur.fetchall()
        cur.close()

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
        traceback.print_exc()
        return jsonify([])

# Dropdown Data
@app.route("/get_dropdown_data")
def get_dropdown_data():
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM Streams")
        streams = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

        cur.execute("SELECT id, name, stream_id FROM Dashboards")
        dashboards = [{"id": row[0], "name": row[1], "stream_id": row[2]} for row in cur.fetchall()]
        cur.close()

        return jsonify({
            "streams": streams,
            "dashboards": dashboards
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username == "admin" and password == "admin":
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# File download
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Delete Ticket
@app.route("/delete_ticket", methods=["POST"])
def delete_ticket():
    data = request.json
    if not data or "id" not in data:
        return jsonify({"error": "Missing ticket ID"}), 400
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tickets WHERE id = ?", (data["id"],))
        conn.commit()
        cur.close()
        return jsonify({"message": "Ticket deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to delete ticket"}), 500

# Run initialization
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
