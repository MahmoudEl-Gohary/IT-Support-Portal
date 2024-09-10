import os
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from datetime import datetime

app = Flask(__name__)

app.secret_key = '123456'
CSV_FILE_PATH = 'tickets.csv'
EXCEL_FILE_PATH = 'data/tickets.xlsx'

ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'password'
}

# Example mappings for location, department, and problem type
LOCATION_CODES = {
    'K Administration Offices': '01', 'Hana Administration Offices': '02', 'Camp': '03', 
    'H Station': '04', 'K Station': '05', 'Arta': '06', 'Hosha': '07', 
    'NWG': '08', 'Hana': '09', 'Main Gate': '10'
}
DEPARTMENT_CODES = {
    'Production': '01', 'Maintenance': '02', 'pet-eng': '03', 'Administration': '04', 
    'Finance': '05', 'Material': '06', 'Projects': '07', 'Security': '08', 
    'Transportation': '09', 'Hygiene': '10', 'Camp Maintenance': '11', 
    'Camp Admin': '12', 'Field Manager': '13', 'Safety': '14', 'Construction': '15', 
    'Heavy Equipment': '16', 'Information Technology': '17', 'Production Accounting': '18'
}
PROBLEM_TYPE_CODES = {
    'software': '1', 'pc': '2', 'network': '3', 'printer': '4', 
    'ip-phone': '5', 'tetra': '6', 'vhf': '7'
}

def ensure_csv_headers():
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Ticket ID', 'Applicant Name', 'Job Title', 'Phone/Ext', 'Date', 'Department', 'Location', 'Problem Type', 'Description', 'Status', 'Report'])
    if not os.path.exists(EXCEL_FILE_PATH):
        df = pd.DataFrame(columns=['Ticket ID', 'Applicant Name', 'Job Title', 'Phone/Ext', 'Date', 'Department', 'Location', 'Problem Type', 'Description', 'Status', 'Report'])
        df.to_excel(EXCEL_FILE_PATH, index=False)

ensure_csv_headers()

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    tickets = []
    view = request.args.get('view', 'list')
    search = request.args.get('search', '')
    location_filter = request.args.get('location', '')
    status_filter = request.args.get('status', '')
    department_filter = request.args.get('department', '')
    problem_type_filter = request.args.get('problem_type', '')
    date_filter = request.args.get('date', '')

    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (not search or search in row['Ticket ID']) and \
               (not location_filter or location_filter == row['Location']) and \
               (not status_filter or status_filter == row['Status']) and \
               (not department_filter or department_filter == row['Department']) and \
               (not problem_type_filter or problem_type_filter == row['Problem Type']) and \
               (not date_filter or date_filter == row['Date']):
                tickets.append(row)

    locations = list(set([ticket['Location'] for ticket in tickets]))
    departments = list(set([ticket['Department'] for ticket in tickets]))
    problem_types = list(set([ticket['Problem Type'] for ticket in tickets]))
    
    return render_template('admin.html', tickets=tickets, view=view, locations=locations, departments=departments, problem_types=problem_types)

@app.route('/create_ticket', methods=['GET', 'POST'])
def create_ticket():
    ensure_csv_headers()  # Ensure the CSV and Excel files exist before processing the request

    if request.method == 'POST':
        applicant_name = request.form['applicant_name']
        job_title = request.form['job_title']
        phone_ext = request.form['phone']
        date = datetime.today().strftime('%Y-%m-%d')  # Automatically set current date
        department = request.form['department']
        location = request.form['location']
        problem_type = request.form['problem_type']
        description = request.form['problem_description']
        status = 'Open'
        report = ''

        # Generate a unique ticket ID
        location_code = LOCATION_CODES.get(location, '00')
        department_code = DEPARTMENT_CODES.get(department, '00')
        problem_type_code = PROBLEM_TYPE_CODES.get(problem_type, '0')
        sequence_number = len(pd.read_csv(CSV_FILE_PATH)) + 1
        ticket_id = int(f"{location_code}{department_code}{problem_type_code}{sequence_number:04d}")

        try:
            # Append to CSV
            with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([ticket_id, applicant_name, job_title, phone_ext, date, department, location, problem_type, description, status, report])

            # Append to Excel
            df = pd.read_csv(CSV_FILE_PATH)
            df.to_excel(EXCEL_FILE_PATH, index=False)
        except PermissionError:
            return "Permission denied: unable to write to the file", 403

        return render_template('ticket_success.html', ticket_id=ticket_id)
    return render_template('create_ticket.html')

@app.route('/status')
def status():
    ticket_id = request.args.get('ticket_id')
    ticket_data = None

    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('Ticket ID') == ticket_id:
                ticket_data = row
                break

    return render_template('status.html', ticket=ticket_data)

@app.route('/update_status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    ticket_id = request.form['ticket_id']
    new_status = request.form['status']
    view = request.args.get('view', 'list')
    updated_tickets = []
    
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('Ticket ID') == ticket_id:
                row['Status'] = new_status
            updated_tickets.append(row)

    with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=updated_tickets[0].keys())
        writer.writeheader()
        writer.writerows(updated_tickets)

    # Update Excel file
    df = pd.read_csv(CSV_FILE_PATH)
    df.to_excel(EXCEL_FILE_PATH, index=False)

    return redirect(url_for('admin', view=view))

@app.route('/write_report', methods=['POST'])
def write_report():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    ticket_id = request.form['ticket_id']
    new_report = request.form['report_text']
    view = request.args.get('view', 'list')
    updated_tickets = []
    
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('Ticket ID') == ticket_id:
                row['Report'] = new_report
            updated_tickets.append(row)

    with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=updated_tickets[0].keys())
        writer.writeheader()
        writer.writerows(updated_tickets)

    # Update Excel file
    df = pd.read_csv(CSV_FILE_PATH)
    df.to_excel(EXCEL_FILE_PATH, index=False)

    return redirect(url_for('admin', view=view))

@app.route('/print_ticket/<ticket_id>')
def print_ticket(ticket_id):
    ticket_data = None

    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get('Ticket ID') == ticket_id:
                ticket_data = row
                break

    return render_template('print_ticket.html', ticket=ticket_data)

@app.route('/print_blank_ticket')
def print_blank_ticket():
    return render_template('print_blank_ticket.html')

if __name__ == '__main__':
    app.run(debug=True)
