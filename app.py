import os
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sqlite3
import uuid

app = Flask(__name__, static_folder='rafey.html', template_folder='rafey.html')
CORS(app)

DB_PATH = 'tickets.db'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard TEXT,
            ticket_no TEXT,
            stream TEXT,
            raised_by TEXT,
            subject TEXT,
            date_logged DATE,
            closed_date DATE,
            priority TEXT,
            status TEXT,
            assigned_to TEXT,
            description TEXT,
            attachment TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
@app.route('/')
def serve_frontend():
    # Optional: serve your rafey.html if placed in frontend folder
    return send_from_directory(app.static_folder, 'rafey.html')

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        tickets = conn.execute('SELECT * FROM tickets').fetchall()
        return jsonify([dict(row) for row in tickets])

@app.route('/api/tickets', methods=['POST'])
def add_ticket():
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('''
            INSERT INTO tickets (subject, priority, status, description, assigned_to)
            VALUES (?, ?, ?, ?, ?)
        ''', (data.get('subject'), data.get('priority'), data.get('status'), data.get('description'), data.get('assigned_to')))
        conn.commit()
        return jsonify({'id': cur.lastrowid}), 201

@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            UPDATE tickets
            SET subject=?, priority=?, status=?, description=?, assigned_to=?
            WHERE id=?
        ''', (data.get('subject'), data.get('priority'), data.get('status'), data.get('description'), data.get('assigned_to'), ticket_id))
        conn.commit()
        return jsonify({'message': 'Ticket updated'})

@app.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('DELETE FROM tickets WHERE id=?', (ticket_id,))
        conn.commit()
        return jsonify({'message': 'Ticket deleted'})

@app.route("/")
def home():
    return render_template("rafey.html")

@app.route("/add_ticket", methods=["POST"])
def add_ticket():
    try:
        # Get form data
        dashboard = request.form.get('dashboard')
        stream = request.form.get('stream')
        raised_by = request.form.get('raised_by')
        subject = request.form.get('subject')
        date_logged = request.form.get('date_logged')
        closed_date = request.form.get('closed_date')
        priority = request.form.get('priority')
        status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        description = request.form.get('description')

        # Handle file upload with unique filename
        attachment = None
        file = request.files.get('attachment')
        if file and file.filename != '' and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            attachment = unique_filename  # store unique filename in DB

        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tickets (
                dashboard, stream, raised_by, subject, date_logged, closed_date,
                priority, status, assigned_to, description, attachment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dashboard, stream, raised_by, subject, date_logged, closed_date,
            priority, status, assigned_to, description, attachment
        ))

        ticket_id = cursor.lastrowid
        ticket_no = f"ARM-{ticket_id:03d}"
        cursor.execute('UPDATE tickets SET ticket_no = ? WHERE id = ?', (ticket_no, ticket_id))

        conn.commit()
        conn.close()

        return jsonify({"message": "Ticket added successfully", "ticket_no": ticket_no}), 200

    except Exception as e:
        print(f"❌ Error inserting ticket: {e}")
        return jsonify({"error": "Failed to add ticket"}), 500

@app.route("/update_ticket", methods=["POST"])
def update_ticket():
    try:
        ticket_id = request.form.get('id')
        if not ticket_id:
            return jsonify({"error": "Missing ticket ID"}), 400

        # Get form data
        dashboard = request.form.get('dashboard')
        ticket_no = request.form.get('ticket_no')
        stream = request.form.get('stream')
        raised_by = request.form.get('raised_by')
        subject = request.form.get('subject')
        date_logged = request.form.get('date_logged')
        closed_date = request.form.get('closed_date')
        priority = request.form.get('priority')
        status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        description = request.form.get('description')

        # Handle file upload - optional, replace old attachment if new file uploaded
        attachment = None
        file = request.files.get('attachment')
        if file and file.filename != '' and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            attachment = unique_filename

        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()

        if attachment:
            cursor.execute('''
                UPDATE tickets SET
                    dashboard = ?, ticket_no = ?, stream = ?, raised_by = ?, subject = ?,
                    date_logged = ?, closed_date = ?, priority = ?, status = ?,
                    assigned_to = ?, description = ?, attachment = ?
                WHERE id = ?
            ''', (
                dashboard, ticket_no, stream, raised_by, subject,
                date_logged, closed_date, priority, status,
                assigned_to, description, attachment,
                ticket_id
            ))
        else:
            cursor.execute('''
                UPDATE tickets SET
                    dashboard = ?, ticket_no = ?, stream = ?, raised_by = ?, subject = ?,
                    date_logged = ?, closed_date = ?, priority = ?, status = ?,
                    assigned_to = ?, description = ?
                WHERE id = ?
            ''', (
                dashboard, ticket_no, stream, raised_by, subject,
                date_logged, closed_date, priority, status,
                assigned_to, description,
                ticket_id
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
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, dashboard, ticket_no, stream, raised_by, subject, date_logged, closed_date,
            priority, status, assigned_to, description, attachment
            FROM tickets ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        tickets = []
        for row in rows:
            attachment_filename = row[12]
            attachment_url = url_for('uploaded_file', filename=attachment_filename) if attachment_filename else None
            tickets.append({
                "id": row[0],
                "dashboard": row[1],
                "ticket_no": row[2],
                "stream": row[3],
                "raised_by": row[4],
                "subject": row[5],
                "date_logged": row[6],
                "closed_date": row[7],
                "priority": row[8],
                "status": row[9],
                "assigned_to": row[10],
                "description": row[11],
                "attachment": attachment_url
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
        conn = sqlite3.connect('tickets.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE id = ?", (data['id'],))
        conn.commit()
        conn.close()
        return jsonify({"message": "Ticket deleted successfully"}), 200
    except Exception as e:
        print(f"❌ Error deleting ticket: {e}")
        return jsonify({"error": "Failed to delete ticket"}), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
