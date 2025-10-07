from flask import Flask, render_template, request, redirect, url_for, Response, flash, session
import pandas as pd
import io
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Secret key for sessions - MUST be set
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")

# Admin credentials from .env with fallbacks
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Create data folder if it doesn't exist
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Path to the joblisting.csv file
JOBLISTING_FILE = os.path.join(DATA_FOLDER, 'joblisting.csv')

def initialize_csv():
    """Create joblisting.csv with headers if it doesn't exist"""
    if not os.path.exists(JOBLISTING_FILE):
        df = pd.DataFrame(columns=["position", "company", "location", "skills", "salary", "link", "created_at"])
        df.to_csv(JOBLISTING_FILE, index=False)

def load_jobs():
    """Load jobs from CSV file"""
    try:
        if os.path.exists(JOBLISTING_FILE):
            df = pd.read_csv(JOBLISTING_FILE)
            # Fill NaN values with empty strings for display
            df = df.fillna('')
            # Convert created_at to datetime if it exists and has values
            if 'created_at' in df.columns and not df.empty:
                try:
                    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                except:
                    pass
            return df
        else:
            initialize_csv()
            return pd.DataFrame(columns=["position", "company", "location", "skills", "salary", "link", "created_at"])
    except Exception as e:
        print(f"Error loading jobs: {str(e)}")
        return pd.DataFrame(columns=["position", "company", "location", "skills", "salary", "link", "created_at"])

def save_jobs(df):
    """Save jobs DataFrame to CSV file"""
    try:
        df.to_csv(JOBLISTING_FILE, index=False)
        return True
    except Exception as e:
        print(f"Error saving jobs: {str(e)}")
        return False

# Home page - View Jobs (recently added first)
@app.route("/")
@app.route("/home")
def view_jobs():
    """Home page displaying up to 10 most recent jobs with search functionality"""
    df = load_jobs()
    query = request.args.get("q", "").strip()
    
    if query and not df.empty:
        # Search in position, company, and skills columns (case-insensitive)
        mask = (
            df['position'].astype(str).str.contains(query, case=False, na=False) |
            df['company'].astype(str).str.contains(query, case=False, na=False) |
            df['skills'].astype(str).str.contains(query, case=False, na=False)
        )
        df = df[mask]
    
    # Sort by created_at descending (most recent first)
    if not df.empty and 'created_at' in df.columns:
        df = df.sort_values('created_at', ascending=False, na_position='last')
    
    # Limit to 10 most recent jobs
    df = df.head(10)
    
    # Convert DataFrame to list of dictionaries for template
    jobs = df.to_dict('records') if not df.empty else []
    
    # Check if user is logged in as admin
    is_admin = session.get('is_admin', False)
    
    return render_template("jobs.html", jobs=jobs, query=query, is_admin=is_admin)

# Add job form
@app.route("/add", methods=["GET", "POST"])
def add_job():
    """Add a new job posting - Admin only"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to add jobs!", "error")
        return redirect(url_for('view_jobs'))
    
    if request.method == "POST":
        try:
            # Load existing jobs
            df = load_jobs()
            
            # Create new job entry
            new_job = {
                "position": request.form.get("position", "").strip(),
                "company": request.form.get("company", "").strip(),
                "location": request.form.get("location", "").strip(),
                "skills": request.form.get("skills", "").strip(),
                "salary": request.form.get("salary", "").strip(),
                "link": request.form.get("link", "").strip(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Validate required fields
            if not new_job["position"] or not new_job["company"]:
                flash("Position and Company are required fields!", "error")
                return render_template("add_job.html", success=False)
            
            # Append new job to DataFrame
            df = pd.concat([df, pd.DataFrame([new_job])], ignore_index=True)
            
            # Save to CSV
            if save_jobs(df):
                flash("Job successfully added!", "success")
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Error adding job!", "error")
                return render_template("add_job.html", success=False)
        
        except Exception as e:
            flash(f"Error adding job: {str(e)}", "error")
            return render_template("add_job.html", success=False)
    
    return render_template("add_job.html", success=False)

# Export Jobs to CSV (Download)
@app.route("/export_csv")
def export_csv():
    """Export jobs to CSV and offer as download - Admin only"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to export jobs!", "error")
        return redirect(url_for('view_jobs'))
    
    df = load_jobs()
    
    if df.empty:
        flash("No jobs to export!", "warning")
        return redirect(url_for("admin_dashboard"))
    
    # Convert DataFrame to CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    response = Response(output.getvalue(), mimetype="text/csv")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response.headers["Content-Disposition"] = f"attachment; filename=jobs_export_{timestamp}.csv"
    
    return response

# Delete a job
@app.route("/delete/<int:job_index>")
def delete_job(job_index):
    """Delete a job by index - Admin only"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to delete jobs!", "error")
        return redirect(url_for('view_jobs'))
    
    try:
        df = load_jobs()
        
        if df.empty or job_index >= len(df) or job_index < 0:
            flash("Job not found!", "error")
            return redirect(url_for("admin_dashboard"))
        
        # Drop the job at the specified index
        df = df.drop(df.index[job_index]).reset_index(drop=True)
        
        # Save updated DataFrame
        if save_jobs(df):
            flash("Job successfully deleted!", "success")
        else:
            flash("Error deleting job!", "error")
        
        return redirect(url_for("admin_dashboard"))
    
    except Exception as e:
        flash(f"Error deleting job: {str(e)}", "error")
        return redirect(url_for("admin_dashboard"))

# Admin Login
@app.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page"""
    # If already logged in, redirect to dashboard
    if session.get('is_admin', False):
        return redirect(url_for('admin_dashboard'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session.permanent = True  # Make session permanent
            flash("Successfully logged in as admin!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password!", "error")
            return render_template("login.html")
    
    return render_template("login.html")

# Admin Logout
@app.route("/logout")
def logout():
    """Logout admin"""
    session.pop('is_admin', None)
    flash("Successfully logged out!", "success")
    return redirect(url_for('view_jobs'))

# Admin Dashboard - View all jobs with CRUD operations
@app.route("/admin/dashboard")
def admin_dashboard():
    """Admin dashboard to manage all jobs"""
    # Check if user is admin
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to access the dashboard!", "error")
        return redirect(url_for('login'))
    
    df = load_jobs()
    
    # Sort by created_at descending (most recent first)
    if not df.empty and 'created_at' in df.columns:
        df = df.sort_values('created_at', ascending=False, na_position='last')
    
    # Convert DataFrame to list of dictionaries with index for deletion
    jobs = []
    for idx, row in df.iterrows():
        job = row.to_dict()
        job['index'] = idx
        # Convert Timestamp to string for template
        if 'created_at' in job and pd.notna(job['created_at']):
            job['created_at'] = str(job['created_at'])
        jobs.append(job)
    
    return render_template("admin_dashboard.html", jobs=jobs)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    flash("Page not found!", "error")
    return redirect(url_for('view_jobs'))

@app.errorhandler(500)
def internal_error(error):
    flash("An internal error occurred. Please try again.", "error")
    return redirect(url_for('view_jobs'))

if __name__ == "__main__":
    # Initialize CSV file on startup
    initialize_csv()
    # Set session lifetime to 7 days
    app.config['PERMANENT_SESSION_LIFETIME'] = 604800
    app.run(debug=True, host='0.0.0.0', port=5000)