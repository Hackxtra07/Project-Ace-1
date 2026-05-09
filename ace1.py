import os
from pymongo import MongoClient
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime

# Hybrid Database Setup
from hybrid_db import HybridDB
uri = "mongodb+srv://manankamboj66_db_user:HeZJf1a7BKEQq3IF@globaldb.jmzxyvp.mongodb.net/?appName=GlobalDB"
hdb = HybridDB(uri, "GlobalDB")

def get_next_sequence(name):
    return hdb.get_next_sequence(name)

# ---------------- Helper Functions ----------------
def show_message(msg):
    messagebox.showinfo("Info", msg)

# ---------------- Main Application ----------------
root = tk.Tk()
root.title("🌸 Project Management Dashboard 🌸")
root.geometry("1400x800")
root.configure(bg="#f0f4f7")

# ---------------- Notebook Tabs ----------------
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True, padx=10, pady=10)

project_tab = tk.Frame(notebook, bg="#f0f4f7")
member_tab = tk.Frame(notebook, bg="#f0f4f7")
task_tab = tk.Frame(notebook, bg="#f0f4f7")
target_tab = tk.Frame(notebook, bg="#f0f4f7")
dashboard_tab = tk.Frame(notebook, bg="#f0f4f7")

notebook.add(project_tab, text="🌟 Projects")
notebook.add(member_tab, text="👥 Members")
notebook.add(task_tab, text="📝 Tasks")
notebook.add(target_tab, text="🎯 Targets")
notebook.add(dashboard_tab, text="📊 Dashboard")

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

# ---------------- PROJECT FUNCTIONS ----------------
def add_project():
    name = project_name_var.get()
    start = project_start_var.get()
    end = project_end_var.get()
    priority = project_priority_var.get()
    if not name or not start:
        show_message("Name and Start Date required!")
        return
    
    project_id = get_next_sequence("project_id")
    hdb.insert_one("Projects", {
        "project_id": project_id,
        "name": name,
        "start_date": start,
        "end_date": end,
        "priority": priority,
        "signed": "No"
    })
    
    clear_project_fields()
    load_projects()
    update_dashboard()
    update_dropdowns()

def update_project():
    selected = project_tree.selection()
    if not selected:
        show_message("Select a project to update!")
        return
    project_id = int(project_tree.item(selected[0])['values'][0])
    name = project_name_var.get()
    start = project_start_var.get()
    end = project_end_var.get()
    priority = project_priority_var.get()
    
    hdb.update_one(
        "Projects",
        {"project_id": project_id},
        {"$set": {"name": name, "start_date": start, "end_date": end, "priority": priority}}
    )
    
    clear_project_fields()
    load_projects()
    update_dashboard()
    update_dropdowns()

def delete_project():
    selected = project_tree.selection()
    if not selected:
        show_message("Select a project to delete!")
        return
    for sel in selected:
        project_id = int(project_tree.item(sel)['values'][0])
        hdb.delete_one("Projects", {"project_id": project_id})
        # Cascade delete
        hdb.delete_many("Tasks", {"project_id": project_id})
        hdb.delete_many("Targets", {"project_id": project_id})
        
    load_projects()
    load_tasks()
    load_targets()
    update_dashboard()
    update_dropdowns()

def clear_project_fields():
    project_name_var.set("")
    project_start_var.set("")
    project_end_var.set("")
    project_priority_var.set("Medium")

def load_projects():
    for row in project_tree.get_children():
        project_tree.delete(row)
    
    projects = hdb.find("Projects", sort_by="project_id")
    for proj in projects:
        val = (proj["project_id"], proj["name"], proj["start_date"], proj["end_date"], proj["priority"], proj.get("signed", "No"))
        project_tree.insert("", "end", values=val, tags=(proj["priority"],))
    
    project_tree.tag_configure("High", background="#f28b82")
    project_tree.tag_configure("Medium", background="#fff475")
    project_tree.tag_configure("Low", background="#ccff90")

def select_project(event):
    selected = project_tree.selection()
    if selected:
        values = project_tree.item(selected[0])['values']
        project_name_var.set(values[1])
        project_start_var.set(values[2])
        project_end_var.set(values[3])
        project_priority_var.set(values[4])

# ---------------- MEMBER FUNCTIONS ----------------
def add_member():
    name = member_name_var.get()
    role = member_role_var.get()
    if not name:
        show_message("Name required!")
        return
    
    member_id = get_next_sequence("member_id")
    hdb.insert_one("TeamMembers", {
        "member_id": member_id,
        "name": name,
        "role": role
    })
    
    clear_member_fields()
    load_members()
    update_dropdowns()

def update_member():
    selected = member_tree.selection()
    if not selected:
        show_message("Select a member to update!")
        return
    member_id = int(member_tree.item(selected[0])['values'][0])
    name = member_name_var.get()
    role = member_role_var.get()
    
    hdb.update_one(
        "TeamMembers",
        {"member_id": member_id},
        {"$set": {"name": name, "role": role}}
    )
    
    clear_member_fields()
    load_members()
    update_dropdowns()

def delete_member():
    selected = member_tree.selection()
    if not selected:
        show_message("Select a member to delete!")
        return
    for sel in selected:
        member_id = int(member_tree.item(sel)['values'][0])
        hdb.delete_one("TeamMembers", {"member_id": member_id})
        # Set assigned_to to None in Tasks
        hdb.update_many("Tasks", {"assigned_to": member_id}, {"$set": {"assigned_to": None}})
        
    load_members()
    load_tasks()
    update_dropdowns()

def clear_member_fields():
    member_name_var.set("")
    member_role_var.set("")

def load_members():
    for row in member_tree.get_children():
        member_tree.delete(row)
    
    members = hdb.find("TeamMembers", sort_by="member_id")
    for mem in members:
        val = (mem["member_id"], mem["name"], mem["role"])
        member_tree.insert("", "end", values=val)

def select_member(event):
    selected = member_tree.selection()
    if selected:
        values = member_tree.item(selected[0])['values']
        member_name_var.set(values[1])
        member_role_var.set(values[2])

# ---------------- TASK FUNCTIONS ----------------
def add_task():
    name = task_name_var.get()
    project_str = task_project_var.get()
    member_str = task_member_var.get()
    due = task_due_var.get()
    status = task_status_var.get()
    comments = task_comments_var.get()
    
    if not name or not project_str:
        show_message("Task Name and Project required!")
        return
    
    try:
        project_id = int(project_str.split(" - ")[0])
        assigned_to = int(member_str.split(" - ")[0]) if member_str else None
    except:
        show_message("Invalid Project or Member selection!")
        return

    task_id = get_next_sequence("task_id")
    hdb.insert_one("Tasks", {
        "task_id": task_id,
        "name": name,
        "project_id": project_id,
        "assigned_to": assigned_to,
        "due_date": due,
        "status": status,
        "comments": comments,
        "signed": "No"
    })
    
    clear_task_fields()
    load_tasks()
    update_dashboard()

def update_task():
    selected = task_tree.selection()
    if not selected:
        show_message("Select a task to update!")
        return
    task_id = int(task_tree.item(selected[0])['values'][0])
    name = task_name_var.get()
    project_str = task_project_var.get()
    member_str = task_member_var.get()
    due = task_due_var.get()
    status = task_status_var.get()
    comments = task_comments_var.get()
    
    try:
        project_id = int(project_str.split(" - ")[0])
        assigned_to = int(member_str.split(" - ")[0]) if member_str else None
    except:
        show_message("Invalid Project or Member selection!")
        return
    
    hdb.update_one(
        "Tasks",
        {"task_id": task_id},
        {"$set": {
            "name": name,
            "project_id": project_id,
            "assigned_to": assigned_to,
            "due_date": due,
            "status": status,
            "comments": comments
        }}
    )
    
    clear_task_fields()
    load_tasks()
    update_dashboard()

def delete_task():
    selected = task_tree.selection()
    if not selected:
        show_message("Select a task to delete!")
        return
    for sel in selected:
        task_id = int(task_tree.item(sel)['values'][0])
        hdb.delete_one("Tasks", {"task_id": task_id})
        
    load_tasks()
    update_dashboard()

def clear_task_fields():
    task_name_var.set("")
    task_project_var.set("")
    task_member_var.set("")
    task_due_var.set("")
    task_status_var.set("Pending")
    task_comments_var.set("")

def load_tasks():
    for row in task_tree.get_children():
        task_tree.delete(row)
    
    tasks = hdb.find("Tasks", sort_by="task_id")
    for task in tasks:
        val = (task["task_id"], task["name"], task["project_id"], task["assigned_to"], task["status"], task["due_date"], task["comments"])
        task_tree.insert("", "end", values=val, tags=(task["status"],))
    
    task_tree.tag_configure("Pending", background="#fff475")
    task_tree.tag_configure("In Progress", background="#aecbfa")
    task_tree.tag_configure("Completed", background="#ccff90")

def select_task(event):
    selected = task_tree.selection()
    if selected:
        values = task_tree.item(selected[0])['values']
        task_name_var.set(values[1])
        # Find project and member strings
        p = hdb.find_one("Projects", {"project_id": int(values[2])})
        task_project_var.set(f"{p['project_id']} - {p['name']}" if p else str(values[2]))
        
        if values[3] and str(values[3]) != "None" and str(values[3]) != "":
            m = hdb.find_one("TeamMembers", {"member_id": int(values[3])})
            task_member_var.set(f"{m['member_id']} - {m['name']}" if m else str(values[3]))
        else:
            task_member_var.set("")
            
        task_status_var.set(values[4])
        task_due_var.set(values[5] if values[5] and str(values[5]) != "None" else "")
        task_comments_var.set(values[6] if values[6] and str(values[6]) != "None" else "")

# ---------------- TARGET FUNCTIONS ----------------
def add_target():
    name = target_name_var.get()
    project_str = target_project_var.get()
    due = target_due_var.get()
    status = target_status_var.get()
    desc = target_desc_var.get()
    
    if not name or not project_str:
        show_message("Target Name and Project required!")
        return
    
    try:
        project_id = int(project_str.split(" - ")[0])
    except:
        show_message("Invalid Project selection!")
        return
        
    target_id = get_next_sequence("target_id")
    hdb.insert_one("Targets", {
        "target_id": target_id,
        "name": name,
        "project_id": project_id,
        "due_date": due,
        "status": status,
        "description": desc
    })
    
    clear_target_fields()
    load_targets()
    update_dashboard()

def update_target():
    selected = target_tree.selection()
    if not selected:
        show_message("Select a target to update!")
        return
    target_id = int(target_tree.item(selected[0])['values'][0])
    name = target_name_var.get()
    project_str = target_project_var.get()
    due = target_due_var.get()
    status = target_status_var.get()
    desc = target_desc_var.get()
    
    try:
        project_id = int(project_str.split(" - ")[0])
    except:
        show_message("Invalid Project selection!")
        return
        
    hdb.update_one(
        "Targets",
        {"target_id": target_id},
        {"$set": {
            "name": name,
            "project_id": project_id,
            "due_date": due,
            "status": status,
            "description": desc
        }}
    )
    
    clear_target_fields()
    load_targets()
    update_dashboard()

def delete_target():
    selected = target_tree.selection()
    if not selected:
        show_message("Select a target to delete!")
        return
    for sel in selected:
        tid = int(target_tree.item(sel)['values'][0])
        hdb.delete_one("Targets", {"target_id": tid})
        
    load_targets()
    update_dashboard()

def clear_target_fields():
    target_name_var.set("")
    target_project_var.set("")
    target_due_var.set("")
    target_status_var.set("Pending")
    target_desc_var.set("")

def load_targets():
    for row in target_tree.get_children():
        target_tree.delete(row)
        
    targets = hdb.find("Targets", sort_by="target_id")
    for t in targets:
        val = (t["target_id"], t["name"], t["project_id"], t["due_date"], t["status"], t["description"])
        target_tree.insert("", "end", values=val, tags=(t["status"],))
        
    target_tree.tag_configure("Pending", background="#fff475")
    target_tree.tag_configure("Completed", background="#ccff90")

def select_target(event):
    selected = target_tree.selection()
    if selected:
        values = target_tree.item(selected[0])['values']
        target_name_var.set(values[1])
        p = hdb.find_one("Projects", {"project_id": int(values[2])})
        target_project_var.set(f"{p['project_id']} - {p['name']}" if p else str(values[2]))
        target_due_var.set(values[3] if values[3] and str(values[3]) != "None" else "")
        target_status_var.set(values[4])
        target_desc_var.set(values[5] if values[5] and str(values[5]) != "None" else "")

# ---------------- DASHBOARD ----------------
def update_dashboard():
    for widget in dashboard_tab.winfo_children():
        widget.destroy()
        
    projects = list(hdb.find("Projects", sort_by="project_id"))
    row=0
    for p in projects:
        pid = p["project_id"]
        total_tasks = hdb.count_documents("Tasks", {"project_id": pid})
        completed_tasks = hdb.count_documents("Tasks", {"project_id": pid, "status": "Completed"})
        progress = int((completed_tasks/total_tasks)*100) if total_tasks else 0

        # Project Card
        card = tk.Frame(dashboard_tab, bg="#ffffff", bd=2, relief="groove")
        card.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        tk.Label(card, text=f"🌸 {p['name']}", font=("Helvetica",14,"bold"), bg="#ffffff").pack(anchor='w', padx=10, pady=5)
        tk.Label(card, text=f"Progress: {progress}%", font=("Helvetica",12), bg="#ffffff").pack(anchor='w', padx=10)
        pb = ttk.Progressbar(card,length=500,maximum=100,value=progress)
        pb.pack(padx=10, pady=5)
        row+=1

def update_dropdowns():
    p_list = [f"{p['project_id']} - {p['name']}" for p in hdb.find("Projects", sort_by="project_id")]
    m_list = [f"{m['member_id']} - {m['name']}" for m in hdb.find("TeamMembers", sort_by="member_id")]
    task_project_dd['values'] = p_list
    task_member_dd['values'] = m_list
    target_project_dd['values'] = p_list

def update_status_bar():
    status = "🟢 Online (MongoDB Atlas)" if hdb.online else "🔴 Offline (Local SQLite)"
    status_label.config(text=status, fg="green" if hdb.online else "red")
    root.after(5000, update_status_bar)

# ---------------- GUI ELEMENTS ----------------

# ---------------- Projects Tab GUI ----------------
proj_frame = tk.Frame(project_tab, bg="#f0f4f7")
proj_frame.pack(side='top', fill='x', padx=10, pady=10)
tk.Label(proj_frame,text="Name", bg="#f0f4f7").grid(row=0,column=0)
tk.Entry(proj_frame,textvariable=project_name_var).grid(row=0,column=1)
tk.Label(proj_frame,text="Start Date", bg="#f0f4f7").grid(row=0,column=2)
DateEntry(proj_frame,textvariable=project_start_var,date_pattern="yyyy-mm-dd").grid(row=0,column=3)
tk.Label(proj_frame,text="End Date", bg="#f0f4f7").grid(row=0,column=4)
DateEntry(proj_frame,textvariable=project_end_var,date_pattern="yyyy-mm-dd").grid(row=0,column=5)
tk.Label(proj_frame,text="Priority", bg="#f0f4f7").grid(row=0,column=6)
ttk.Combobox(proj_frame,textvariable=project_priority_var,values=["High","Medium","Low"]).grid(row=0,column=7)
tk.Button(proj_frame,text="Add",command=add_project,bg="#5dade2",fg="white").grid(row=0,column=8,padx=5)
tk.Button(proj_frame,text="Update",command=update_project,bg="#58d68d",fg="white").grid(row=0,column=9,padx=5)
tk.Button(proj_frame,text="Delete",command=delete_project,bg="#e74c3c",fg="white").grid(row=0,column=10,padx=5)

project_tree = ttk.Treeview(project_tab, columns=("ID","Name","Start","End","Priority","Signed"), show="headings")
for col in project_tree["columns"]:
    project_tree.heading(col,text=col)
project_tree.pack(fill='both',expand=True,padx=10,pady=10)
project_tree.bind("<<TreeviewSelect>>",select_project)
load_projects()

# ---------------- Members Tab GUI ----------------
mem_frame = tk.Frame(member_tab, bg="#f0f4f7")
mem_frame.pack(side='top', fill='x', padx=10, pady=10)
tk.Label(mem_frame,text="Name", bg="#f0f4f7").grid(row=0,column=0)
tk.Entry(mem_frame,textvariable=member_name_var).grid(row=0,column=1)
tk.Label(mem_frame,text="Role", bg="#f0f4f7").grid(row=0,column=2)
tk.Entry(mem_frame,textvariable=member_role_var).grid(row=0,column=3)
tk.Button(mem_frame,text="Add",command=add_member,bg="#5dade2",fg="white").grid(row=0,column=4,padx=5)
tk.Button(mem_frame,text="Update",command=update_member,bg="#58d68d",fg="white").grid(row=0,column=5,padx=5)
tk.Button(mem_frame,text="Delete",command=delete_member,bg="#e74c3c",fg="white").grid(row=0,column=6,padx=5)

member_tree = ttk.Treeview(member_tab, columns=("ID","Name","Role"), show="headings")
for col in member_tree["columns"]:
    member_tree.heading(col,text=col)
member_tree.pack(fill='both',expand=True,padx=10,pady=10)
member_tree.bind("<<TreeviewSelect>>",select_member)
load_members()

# ---------------- Tasks Tab GUI ----------------
task_frame = tk.Frame(task_tab, bg="#f0f4f7")
task_frame.pack(side='top', fill='x', padx=10, pady=10)
tk.Label(task_frame,text="Name", bg="#f0f4f7").grid(row=0,column=0)
tk.Entry(task_frame,textvariable=task_name_var).grid(row=0,column=1)
tk.Label(task_frame,text="Project", bg="#f0f4f7").grid(row=0,column=2)
task_project_dd = ttk.Combobox(task_frame,textvariable=task_project_var)
task_project_dd.grid(row=0,column=3)
tk.Label(task_frame,text="Assign To", bg="#f0f4f7").grid(row=0,column=4)
task_member_dd = ttk.Combobox(task_frame,textvariable=task_member_var)
task_member_dd.grid(row=0,column=5)
tk.Label(task_frame,text="Status", bg="#f0f4f7").grid(row=0,column=6)
ttk.Combobox(task_frame,textvariable=task_status_var,values=["Pending","In Progress","Completed"]).grid(row=0,column=7)
tk.Label(task_frame,text="Due Date", bg="#f0f4f7").grid(row=0,column=8)
DateEntry(task_frame,textvariable=task_due_var,date_pattern="yyyy-mm-dd").grid(row=0,column=9)
tk.Label(task_frame,text="Comments", bg="#f0f4f7").grid(row=0,column=10)
tk.Entry(task_frame,textvariable=task_comments_var).grid(row=0,column=11)
tk.Button(task_frame,text="Add",command=add_task,bg="#5dade2",fg="white").grid(row=0,column=12,padx=5)
tk.Button(task_frame,text="Update",command=update_task,bg="#58d68d",fg="white").grid(row=0,column=13,padx=5)
tk.Button(task_frame,text="Delete",command=delete_task,bg="#e74c3c",fg="white").grid(row=0,column=14,padx=5)

task_tree = ttk.Treeview(task_tab, columns=("ID","Name","ProjectID","AssignedTo","Status","DueDate","Comments"), show="headings")
for col in task_tree["columns"]:
    task_tree.heading(col,text=col)
task_tree.pack(fill='both',expand=True,padx=10,pady=10)
task_tree.bind("<<TreeviewSelect>>",select_task)
load_tasks()

# ---------------- Targets Tab GUI ----------------
target_frame = tk.Frame(target_tab, bg="#f0f4f7")
target_frame.pack(side='top', fill='x', padx=10, pady=10)
tk.Label(target_frame,text="Name", bg="#f0f4f7").grid(row=0,column=0)
tk.Entry(target_frame,textvariable=target_name_var).grid(row=0,column=1)
tk.Label(target_frame,text="Project", bg="#f0f4f7").grid(row=0,column=2)
target_project_dd = ttk.Combobox(target_frame,textvariable=target_project_var)
target_project_dd.grid(row=0,column=3)
tk.Label(target_frame,text="Status", bg="#f0f4f7").grid(row=0,column=4)
ttk.Combobox(target_frame,textvariable=target_status_var,values=["Pending","Completed"]).grid(row=0,column=5)
tk.Label(target_frame,text="Due Date", bg="#f0f4f7").grid(row=0,column=6)
DateEntry(target_frame,textvariable=target_due_var,date_pattern="yyyy-mm-dd").grid(row=0,column=7)
tk.Label(target_frame,text="Description", bg="#f0f4f7").grid(row=0,column=8)
tk.Entry(target_frame,textvariable=target_desc_var).grid(row=0,column=9)
tk.Button(target_frame,text="Add",command=add_target,bg="#5dade2",fg="white").grid(row=0,column=10,padx=5)
tk.Button(target_frame,text="Update",command=update_target,bg="#58d68d",fg="white").grid(row=0,column=11,padx=5)
tk.Button(target_frame,text="Delete",command=delete_target,bg="#e74c3c",fg="white").grid(row=0,column=12,padx=5)

target_tree = ttk.Treeview(target_tab, columns=("ID","Name","ProjectID","DueDate","Status","Description"), show="headings")
for col in target_tree["columns"]:
    target_tree.heading(col,text=col)
target_tree.pack(fill='both',expand=True,padx=10,pady=10)
target_tree.bind("<<TreeviewSelect>>",select_target)
load_targets()

# ---------------- Status Bar ----------------
status_frame = tk.Frame(root, bg="#f0f4f7")
status_frame.pack(side='bottom', fill='x', padx=10)
status_label = tk.Label(status_frame, text="Checking Status...", font=("Helvetica", 10, "italic"), bg="#f0f4f7")
status_label.pack(side='right')

# ---------------- Initialize ----------------
update_dropdowns()
update_dashboard()
update_status_bar()

root.mainloop()
