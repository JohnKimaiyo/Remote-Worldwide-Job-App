from flask import Flask, render_template, request, redirect, url_for, Response, flash, session
import pandas as pd
import io
import os
from datetime import datetime
from dotenv import load_dotenv
import re

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

# Path to the CSV files
JOBLISTING_FILE = os.path.join(DATA_FOLDER, 'joblisting.csv')
SUBSCRIBERS_FILE = os.path.join(DATA_FOLDER, 'subscribers.csv')

def initialize_csv():
    """Create CSV files with headers if they don't exist"""
    if not os.path.exists(JOBLISTING_FILE):
        df = pd.DataFrame(columns=["position", "company", "location", "skills", "salary", "link", "created_at"])
        df.to_csv(JOBLISTING_FILE, index=False)
    
    # Initialize subscribers CSV
    if not os.path.exists(SUBSCRIBERS_FILE):
        df = pd.DataFrame(columns=["email", "subscribed_at", "is_active"])
        df.to_csv(SUBSCRIBERS_FILE, index=False)

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

def load_subscribers():
    """Load subscribers from CSV file"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            df = pd.read_csv(SUBSCRIBERS_FILE)
            return df.fillna('')
        else:
            return pd.DataFrame(columns=["email", "subscribed_at", "is_active"])
    except Exception as e:
        print(f"Error loading subscribers: {str(e)}")
        return pd.DataFrame(columns=["email", "subscribed_at", "is_active"])

def save_subscribers(df):
    """Save subscribers DataFrame to CSV file"""
    try:
        df.to_csv(SUBSCRIBERS_FILE, index=False)
        return True
    except Exception as e:
        print(f"Error saving subscribers: {str(e)}")
        return False

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def add_subscriber(email):
    """Add a new subscriber"""
    df = load_subscribers()
    
    # Check if email already exists and is active
    if not df.empty and email.lower() in df['email'].str.lower().values:
        # Check if it's active or inactive
        existing = df[df['email'].str.lower() == email.lower()]
        if not existing.empty and existing.iloc[0]['is_active']:
            return False, "This email is already subscribed!"
        else:
            # Reactivate the subscription
            df.loc[df['email'].str.lower() == email.lower(), 'is_active'] = True
            df.loc[df['email'].str.lower() == email.lower(), 'subscribed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return save_subscribers(df), "Successfully resubscribed to job notifications!"
    
    new_subscriber = {
        "email": email.lower(),
        "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_active": True
    }
    
    df = pd.concat([df, pd.DataFrame([new_subscriber])], ignore_index=True)
    return save_subscribers(df), "Successfully subscribed to job notifications!"

def get_active_subscribers():
    """Get list of active subscriber emails"""
    df = load_subscribers()
    if df.empty:
        return []
    
    active = df[df['is_active'] == True]['email'].tolist()
    return active

def notify_subscribers(job_data):
    """
    Notify subscribers about new job posting
    This is a placeholder function - you'll need to implement actual email sending
    using services like SendGrid, AWS SES, or SMTP
    """
    subscribers = get_active_subscribers()
    
    if not subscribers:
        return
    
    # TODO: Implement email sending logic here
    # Example with SendGrid or SMTP:
    # for email in subscribers:
    #     send_email(
    #         to=email,
    #         subject=f"New Job: {job_data['position']} at {job_data['company']}",
    #         body=f"A new job has been posted:\n\nPosition: {job_data['position']}\nCompany: {job_data['company']}\nLocation: {job_data['location']}\n..."
    #     )
    
    print(f"Would notify {len(subscribers)} subscribers about: {job_data['position']} at {job_data['company']}")

# Home page - View Jobs (recently added first)
@app.route("/")
@app.route("/home")
def view_jobs():
    """Home page displaying up to 10 most recent jobs with search functionality"""
    df = load_jobs()
    query = request.args.get("q", "").strip()
    
    # Check for subscription success message
    subscribed = request.args.get("subscribed", "")
    if subscribed == "success":
        flash("Thank you for subscribing! You'll receive email notifications for new jobs.", "success")
    elif subscribed == "exists":
        flash("This email is already subscribed!", "warning")
    
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
    
    # Get total subscriber count
    subscribers_df = load_subscribers()
    subscriber_count = len(subscribers_df[subscribers_df['is_active'] == True]) if not subscribers_df.empty else 0
    
    return render_template("jobs.html", jobs=jobs, query=query, is_admin=is_admin, subscriber_count=subscriber_count)

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
                # Notify subscribers about the new job
                notify_subscribers(new_job)
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
    
    # Get subscriber count
    subscribers_df = load_subscribers()
    subscriber_count = len(subscribers_df[subscribers_df['is_active'] == True]) if not subscribers_df.empty else 0
    
    return render_template("admin_dashboard.html", jobs=jobs, subscriber_count=subscriber_count)

# Subscribe to job notifications
@app.route("/subscribe", methods=["POST"])
def subscribe():
    """Subscribe to job notifications"""
    email = request.form.get("email", "").strip().lower()
    
    # Validate email format
    if not email or not is_valid_email(email):
        flash("Please enter a valid email address!", "error")
        return redirect(url_for('view_jobs'))
    
    success, message = add_subscriber(email)
    
    if success:
        flash(message, "success")
        return redirect(url_for('view_jobs', subscribed='success'))
    else:
        flash(message, "warning")
        return redirect(url_for('view_jobs', subscribed='exists'))

# Unsubscribe from notifications
@app.route("/unsubscribe", methods=["GET", "POST"])
def unsubscribe():
    """Unsubscribe from job notifications"""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        if not email or not is_valid_email(email):
            flash("Please enter a valid email address!", "error")
            return render_template("unsubscribe.html")
        
        df = load_subscribers()
        
        if df.empty or email not in df['email'].str.lower().values:
            flash("Email address not found in subscribers list!", "error")
            return render_template("unsubscribe.html")
        
        # Mark as inactive instead of deleting
        df.loc[df['email'].str.lower() == email, 'is_active'] = False
        
        if save_subscribers(df):
            flash("Successfully unsubscribed from job notifications!", "success")
        else:
            flash("Error unsubscribing. Please try again.", "error")
        
        return render_template("unsubscribe.html")
    
    return render_template("unsubscribe.html")

# Admin view subscribers
@app.route("/admin/subscribers")
def view_subscribers():
    """View all subscribers - Admin only"""
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to view subscribers!", "error")
        return redirect(url_for('login'))
    
    df = load_subscribers()
    
    # Sort by subscribed_at descending
    if not df.empty and 'subscribed_at' in df.columns:
        df = df.sort_values('subscribed_at', ascending=False, na_position='last')
    
    # Convert to list of dicts
    subscribers = df.to_dict('records') if not df.empty else []
    
    # Count active subscribers
    active_count = len(df[df['is_active'] == True]) if not df.empty else 0
    
    return render_template("subscribers.html", subscribers=subscribers, active_count=active_count)

# Export subscribers to CSV
@app.route("/admin/subscribers/export")
def export_subscribers():
    """Export subscribers to CSV - Admin only"""
    if not session.get('is_admin', False):
        flash("You must be logged in as admin to export subscribers!", "error")
        return redirect(url_for('view_jobs'))
    
    df = load_subscribers()
    
    if df.empty:
        flash("No subscribers to export!", "warning")
        return redirect(url_for("view_subscribers"))
    
    # Convert DataFrame to CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    response = Response(output.getvalue(), mimetype="text/csv")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response.headers["Content-Disposition"] = f"attachment; filename=subscribers_export_{timestamp}.csv"
    
    return response

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
    # Initialize CSV files on startup
    initialize_csv()
    # Set session lifetime to 7 days
    app.config['PERMANENT_SESSION_LIFETIME'] = 604800
    app.run(debug=True, host='0.0.0.0', port=5000)