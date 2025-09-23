import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ---------------- Database ----------------
conn = sqlite3.connect("project_management.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS Projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    priority TEXT,
    signed TEXT DEFAULT 'No'
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS TeamMembers (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS Tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    name TEXT NOT NULL,
    assigned_to INTEGER,
    status TEXT DEFAULT 'Pending',
    due_date TEXT,
    comments TEXT,
    signed TEXT DEFAULT 'No',
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES TeamMembers(member_id) ON DELETE SET NULL
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS Targets (
    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    name TEXT NOT NULL,
    due_date TEXT,
    status TEXT DEFAULT 'Pending',
    description TEXT,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE
)""")
conn.commit()

# ---------------- Helper ----------------
def show_message(msg):
    messagebox.showinfo("Info", msg)

# ---------------- Main Window ----------------
root = tk.Tk()
root.title("Project Management Dashboard")
root.geometry("1400x800")
root.configure(bg="#f5f5f5")

# ---------------- Variables ----------------
project_name_var = tk.StringVar()
project_start_var = tk.StringVar()
project_end_var = tk.StringVar()
project_priority_var = tk.StringVar(value="Medium")

member_name_var = tk.StringVar()
member_role_var = tk.StringVar()

task_name_var = tk.StringVar()
task_project_var = tk.StringVar()
task_member_var = tk.StringVar()
task_due_var = tk.StringVar()
task_status_var = tk.StringVar(value="Pending")
task_comments_var = tk.StringVar()

target_name_var = tk.StringVar()
target_project_var = tk.StringVar()
target_due_var = tk.StringVar()
target_status_var = tk.StringVar(value="Pending")
target_desc_var = tk.StringVar()

# ---------------- FUNCTIONS ----------------
def add_project():
    name = project_name_var.get()
    start = project_start_var.get()
    end = project_end_var.get()
    priority = project_priority_var.get()
    if not name or not start:
        show_message("Name and Start Date required!")
        return
    try:
        datetime.strptime(start,"%Y-%m-%d")
        if end:
            datetime.strptime(end,"%Y-%m-%d")
    except:
        show_message("Invalid date format! Use YYYY-MM-DD")
        return
    cursor.execute("INSERT INTO Projects (name,start_date,end_date,priority) VALUES (?,?,?,?)",(name,start,end,priority))
    conn.commit()
    clear_project_fields()
    load_projects()
    update_dashboard_cards()

def load_projects():
    for row in project_tree.get_children():
        project_tree.delete(row)
    cursor.execute("SELECT * FROM Projects")
    for proj in cursor.fetchall():
        project_tree.insert("", "end", values=proj, tags=(proj[4],))
    project_tree.tag_configure("High", background="#ff9999")
    project_tree.tag_configure("Medium", background="#fff799")
    project_tree.tag_configure("Low", background="#b3ffb3")

def clear_project_fields():
    project_name_var.set("")
    project_start_var.set("")
    project_end_var.set("")
    project_priority_var.set("Medium")

def select_project(event):
    sel = project_tree.selection()
    if sel:
        vals = project_tree.item(sel[0])['values']
        project_name_var.set(vals[1])
        project_start_var.set(vals[2])
        project_end_var.set(vals[3])
        project_priority_var.set(vals[4])

# ---------------- Dashboard Cards ----------------
def update_dashboard_cards():
    for widget in stats_frame.winfo_children():
        widget.destroy()
    # Fetch counts
    cursor.execute("SELECT COUNT(*) FROM Projects")
    total_projects = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Tasks")
    total_tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Tasks WHERE status='Completed'")
    completed_tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Tasks WHERE status='Pending'")
    pending_tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM TeamMembers")
    total_members = cursor.fetchone()[0]

    # Card data
    cards = [
        ("Total Projects", total_projects, "#5dade2"),
        ("Total Tasks", total_tasks, "#58d68d"),
        ("Completed Tasks", completed_tasks, "#f4d03f"),
        ("Pending Tasks", pending_tasks, "#ec7063"),
        ("Total Members", total_members, "#af7ac5")
    ]
    col=0
    for title,count,color in cards:
        card = tk.Frame(stats_frame,bg=color,width=200,height=100,bd=0,relief="raised")
        card.grid(row=0,column=col,padx=20,pady=10)
        tk.Label(card,text=title,bg=color,fg="white",font=("Helvetica",12,"bold")).pack(pady=10)
        tk.Label(card,text=str(count),bg=color,fg="white",font=("Helvetica",18,"bold")).pack()
        col+=1

# ---------------- GUI ----------------
# Top Stats Cards
stats_frame = tk.Frame(root,bg="#f5f5f5")
stats_frame.pack(fill="x",pady=10)

# Projects Section
proj_frame = tk.LabelFrame(root,text="Projects",bg="white",font=("Helvetica",12,"bold"),padx=10,pady=10)
proj_frame.pack(fill="x",padx=20,pady=5)

tk.Label(proj_frame,text="Name:",bg="white").grid(row=0,column=0,padx=5,pady=5)
tk.Entry(proj_frame,textvariable=project_name_var).grid(row=0,column=1,padx=5,pady=5)
tk.Label(proj_frame,text="Start:",bg="white").grid(row=0,column=2,padx=5,pady=5)
tk.Entry(proj_frame,textvariable=project_start_var).grid(row=0,column=3,padx=5,pady=5)
tk.Label(proj_frame,text="End:",bg="white").grid(row=0,column=4,padx=5,pady=5)
tk.Entry(proj_frame,textvariable=project_end_var).grid(row=0,column=5,padx=5,pady=5)
tk.Label(proj_frame,text="Priority:",bg="white").grid(row=0,column=6,padx=5,pady=5)
ttk.Combobox(proj_frame,textvariable=project_priority_var,values=["High","Medium","Low"]).grid(row=0,column=7,padx=5,pady=5)
tk.Button(proj_frame,text="Add",bg="#5dade2",fg="white",command=add_project).grid(row=0,column=8,padx=5,pady=5)

# Projects Treeview
project_tree = ttk.Treeview(root, columns=("ID","Name","Start","End","Priority","Signed"), show="headings")
for col in project_tree["columns"]:
    project_tree.heading(col,text=col)
project_tree.pack(fill="both",expand=True,padx=20,pady=10)
project_tree.bind("<<TreeviewSelect>>",select_project)
load_projects()
update_dashboard_cards()

root.mainloop()
