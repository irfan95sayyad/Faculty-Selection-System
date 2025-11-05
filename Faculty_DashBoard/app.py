# faculty_selection_app.py
import streamlit as st
import pandas as pd
import os
from io import BytesIO
import plotly.express as px

# -----------------------
# Persistent data directory & filenames
# -----------------------

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

SUBJECTS_FILE = os.path.join(DATA_DIR, "subjects.csv")        # Year,Subject_Code,Subject_Name
FACULTY_FILE = os.path.join(DATA_DIR, "faculty_list.csv")     # Faculty_ID,Faculty_Name,Department,Designation,Email (prefer Faculty_Name)
CHOICE_FILE = os.path.join(DATA_DIR, "student_choices.csv")   # Regd_No,Name,Year,Section,Subject_Code,Subject_Name,Faculty_Selected
FAC_AVAIL_FILE = os.path.join(DATA_DIR, "faculty_availability.csv")  # Faculty_Name,Subject_Code,Subject_Name,Available (Yes/No)

# -----------------------
# Ensure data files exist with proper headers (so admin can see files in repo & Streamlit Cloud preserves them)
# -----------------------
def ensure_file_with_headers(path, headers):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=headers)
        df.to_csv(path, index=False, encoding="utf-8")

def ensure_data_files():
    ensure_file_with_headers(SUBJECTS_FILE, ["Year", "Subject_Code", "Subject_Name"])
    ensure_file_with_headers(FACULTY_FILE, ["Faculty_Name"])
    ensure_file_with_headers(CHOICE_FILE, ["Regd_No","Name","Year","Section","Subject_Code","Subject_Name","Faculty_Selected"])
    ensure_file_with_headers(FAC_AVAIL_FILE, ["Faculty_Name","Subject_Code","Subject_Name","Available"])

ensure_data_files()

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="Faculty Preference System", layout="wide")
st.title("🎓 Department Faculty Preference System (Students • Faculty • Admin)")

# -----------------------
# Helper functions
# -----------------------
@st.cache_data(ttl=60)
def load_subjects():
    try:
        return pd.read_csv(SUBJECTS_FILE, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["Year", "Subject_Code", "Subject_Name"])

@st.cache_data(ttl=60)
def load_faculty():
    try:
        df = pd.read_csv(FACULTY_FILE, dtype=str)
        # Normalize to have Faculty_Name column
        if "Faculty_Name" not in df.columns and df.shape[1] > 0:
            df = df.rename(columns={df.columns[0]: "Faculty_Name"})
        return df
    except Exception:
        return pd.DataFrame(columns=["Faculty_Name"])

def load_choices():
    try:
        return pd.read_csv(CHOICE_FILE, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["Regd_No","Name","Year","Section","Subject_Code","Subject_Name","Faculty_Selected"])

def load_availability():
    try:
        return pd.read_csv(FAC_AVAIL_FILE, dtype=str)
    except Exception:
        return pd.DataFrame(columns=["Faculty_Name","Subject_Code","Subject_Name","Available"])

def save_df_to_csv(df, path):
    # overwrite safely
    df.to_csv(path, index=False, encoding="utf-8", mode="w")

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return out.getvalue()

# -----------------------
# Sidebar: Mode selection & simple admin login
# -----------------------
mode = st.sidebar.radio("Select Mode", ["Student Section", "Faculty View", "Admin View"])

# Admin password (change this in code as needed)
ADMIN_PASSWORD = "admin@123"

if mode == "Admin View":
    st.sidebar.write("🔒 Admin Login")
    admin_pw = st.sidebar.text_input("Enter admin password", type="password")
    if admin_pw != ADMIN_PASSWORD:
        st.sidebar.warning("Enter correct password to access Admin features.")
        st.stop()

# -----------------------
# Load existing dataframes
# -----------------------
subjects_df = load_subjects()
faculty_df = load_faculty()
choices_df = load_choices()
avail_df = load_availability()

# Initialize availability if possible and empty
def initialize_availability_if_empty():
    global avail_df
    if faculty_df.empty or subjects_df.empty:
        return
    if avail_df.empty:
        rows = []
        for _, frow in faculty_df.iterrows():
            fname = frow.get("Faculty_Name") if "Faculty_Name" in frow.index else frow.iloc[0]
            for _, srow in subjects_df.iterrows():
                rows.append({
                    "Faculty_Name": fname,
                    "Subject_Code": srow["Subject_Code"],
                    "Subject_Name": srow["Subject_Name"],
                    "Available": "Yes"
                })
        avail_df = pd.DataFrame(rows)
        save_df_to_csv(avail_df, FAC_AVAIL_FILE)

initialize_availability_if_empty()

# -----------------------
# ADMIN VIEW
# -----------------------
if mode == "Admin View":
    st.header("🧑‍🏫 Admin Dashboard")
    st.markdown("Upload or view `subjects.csv` and `faculty_list.csv`. Admin can also view faculty availability and student selections.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Upload subjects (Year, Subject_Code, Subject_Name)")
        uploaded_subjects = st.file_uploader("Upload subjects.csv", type=["csv"], key="sub_upload")
        if uploaded_subjects is not None:
            try:
                df_sub = pd.read_csv(uploaded_subjects, dtype=str)
                required = {"Year","Subject_Code","Subject_Name"}
                if not required.issubset(set(df_sub.columns)):
                    st.error(f"subjects.csv must contain columns: {required}")
                else:
                    df_sub.to_csv(SUBJECTS_FILE, index=False, encoding="utf-8")
                    st.success("subjects.csv uploaded and saved.")
                    # refresh cached data
                    subjects_df = df_sub
                    # reinitialize availability (if needed)
                    initialize_availability_if_empty()
            except Exception as e:
                st.error(f"Error reading file: {e}")

        st.write("Current subjects dataframe:")
        st.dataframe(subjects_df)

    with col2:
        st.subheader("Upload faculty list (Faculty_Name preferred column)")
        uploaded_faculty = st.file_uploader("Upload faculty_list.csv", type=["csv"], key="fac_upload")
        if uploaded_faculty is not None:
            try:
                df_fac = pd.read_csv(uploaded_faculty, dtype=str)
                # try to detect faculty name column
                if "Faculty_Name" not in df_fac.columns:
                    # attempt to find a likely name column
                    candidate = None
                    for c in df_fac.columns:
                        if "name" in c.lower():
                            candidate = c
                            break
                    if candidate:
                        df_fac = df_fac.rename(columns={candidate: "Faculty_Name"})
                    else:
                        st.error("faculty_list.csv must contain a Faculty_Name column (or a column with 'name' in its header).")
                        st.stop()
                df_fac.to_csv(FACULTY_FILE, index=False, encoding="utf-8")
                st.success("faculty_list.csv uploaded and saved.")
                faculty_df = df_fac
                # reinitialize availability (if needed)
                initialize_availability_if_empty()
            except Exception as e:
                st.error(f"Error reading file: {e}")

        st.write("Current faculty list:")
        st.dataframe(faculty_df)

    st.markdown("---")
    st.subheader("Student Selections Data")
    choices_df = load_choices()
    if choices_df.empty:
        st.info("No student selections recorded yet.")
    else:
        st.dataframe(choices_df)

        # Summary: count of selections per Subject vs Faculty
        st.subheader("Summary: No. of students choosing each faculty for each subject")
        summary = (choices_df.groupby(["Subject_Code","Subject_Name","Faculty_Selected"])
                          .size().reset_index(name="No_of_Students"))
        st.dataframe(summary)

        # Pivot table
        pivot = summary.pivot_table(index=["Subject_Code","Subject_Name"], columns="Faculty_Selected",
                                    values="No_of_Students", fill_value=0)
        st.write("### Pivot: Subjects × Faculty (counts)")
        st.dataframe(pivot.reset_index())

        # Table: For each faculty, which subjects were chosen and by whom
        st.subheader("Faculty → Chosen Subjects (detailed)")
        st.write("This table lists each student choice; you can filter/sort as needed.")
        st.dataframe(choices_df.sort_values(["Subject_Code","Faculty_Selected"]))

        # Downloads
        st.markdown("### Export reports")
        csv_summary = summary.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download summary CSV", data=csv_summary, file_name="faculty_summary.csv", mime="text/csv")
        st.download_button("📥 Download detailed choices CSV", data=choices_df.to_csv(index=False).encode("utf-8"),
                           file_name="student_choices_detailed.csv", mime="text/csv")
        st.download_button("📥 Download pivot as Excel", data=to_excel_bytes(pivot.reset_index()), file_name="subject_faculty_pivot.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # -----------------------
        # Charts: Top chosen faculty per subject (bar) and faculty workload (pie)
        # -----------------------
        st.markdown("---")
        st.subheader("Visualizations")

        # Bar chart: for each subject show top N faculties or plot grouped bars
        st.write("**Bar Chart — Faculty choices per subject (stacked/grouped)**")
        # allow subject selection
        subject_choices = summary["Subject_Code"].unique().tolist()
        chosen_subject = st.selectbox("Select subject to visualize", options=subject_choices) if len(subject_choices) > 0 else None
        if chosen_subject:
            df_sub_summary = summary[summary["Subject_Code"] == chosen_subject]
            if df_sub_summary.empty:
                st.info("No choices for selected subject yet.")
            else:
                fig = px.bar(df_sub_summary.sort_values("No_of_Students", ascending=False),
                             x="Faculty_Selected", y="No_of_Students",
                             labels={"Faculty_Selected":"Faculty", "No_of_Students":"No. of Students"},
                             title=f"Choices for {chosen_subject} — {df_sub_summary['Subject_Name'].iloc[0]}")
                st.plotly_chart(fig, use_container_width=True)

        # Combined bar: grouped by subject (top faculties across subjects)
        st.write("**Combined bar — all subjects (faculties grouped by subject)**")
        if not summary.empty:
            fig2 = px.bar(summary, x="Subject_Code", y="No_of_Students",
                          color="Faculty_Selected", barmode="group",
                          labels={"Subject_Code":"Subject", "No_of_Students":"No. of Students", "Faculty_Selected":"Faculty"})
            st.plotly_chart(fig2, use_container_width=True)

        # Pie chart: workload distribution (total choices per faculty)
        st.write("**Pie Chart — Faculty workload distribution (total selections)**")
        faculty_counts = choices_df.groupby("Faculty_Selected").size().reset_index(name="No_of_Students")
        if not faculty_counts.empty:
            fig3 = px.pie(faculty_counts, names="Faculty_Selected", values="No_of_Students",
                          title="Total student selections per faculty")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No faculty selection data yet for pie chart.")

    st.markdown("---")
    st.subheader("Faculty Availability (what faculty marked as available)")
    avail_df = load_availability()
    if avail_df.empty:
        st.info("No faculty availability data found. It will be initialized when faculty first set their availability or when admin and subjects are uploaded.")
    else:
        st.dataframe(avail_df)
        st.markdown("### Availability Pivot (Subjects × Faculty)")
        try:
            pivot_avail = avail_df.pivot_table(index=["Subject_Code","Subject_Name"], columns="Faculty_Name",
                                           values="Available", aggfunc=lambda x: ", ".join(x.astype(str))).fillna("")
            st.dataframe(pivot_avail.reset_index())
        except Exception:
            st.info("Availability pivot could not be rendered (maybe many faculty).")

        # Export availability
        st.download_button("📥 Download availability CSV", data=avail_df.to_csv(index=False).encode("utf-8"),
                           file_name="faculty_availability.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Admin Utilities")
    if st.button("Clear all student choices (DELETE student_choices.csv)"):
        if os.path.exists(CHOICE_FILE):
            os.remove(CHOICE_FILE)
        # recreate empty file with headers
        ensure_file_with_headers(CHOICE_FILE, ["Regd_No","Name","Year","Section","Subject_Code","Subject_Name","Faculty_Selected"])
        st.success("All student choices cleared.")
        st.rerun()

    if st.button("Initialize / Reset faculty availability (recreate availability rows)"):
        # Recreate default availability (Yes) for every faculty × subject
        if faculty_df.empty or subjects_df.empty:
            st.error("Upload faculty_list.csv and subjects.csv first.")
        else:
            rows = []
            for _, frow in faculty_df.iterrows():
                fname = frow.get("Faculty_Name") if "Faculty_Name" in frow.index else frow.iloc[0]
                for _, srow in subjects_df.iterrows():
                    rows.append({
                        "Faculty_Name": fname,
                        "Subject_Code": srow["Subject_Code"],
                        "Subject_Name": srow["Subject_Name"],
                        "Available": "Yes"
                    })
            avail_df = pd.DataFrame(rows)
            save_df_to_csv(avail_df, FAC_AVAIL_FILE)
            st.success("Faculty availability has been (re)initialized.")
            st.rerun()

# -----------------------
# FACULTY VIEW
# -----------------------
elif mode == "Faculty View":
    st.header("🧑‍🏫 Faculty Dashboard")
    if faculty_df.empty:
        st.warning("Admin must upload faculty_list.csv first.")
        st.stop()

    # Choose faculty by name
    if "Faculty_Name" in faculty_df.columns:
        faculty_names = sorted(faculty_df["Faculty_Name"].dropna().unique().tolist())
    else:
        faculty_names = sorted(faculty_df.iloc[:,0].dropna().unique().tolist())

    selected_faculty = st.selectbox("Select your name", faculty_names)

    if selected_faculty:
        st.success(f"Logged in as: {selected_faculty}")
        # Show students who selected this faculty
        choices_df = load_choices()
        my_students = choices_df[choices_df["Faculty_Selected"] == selected_faculty] if not choices_df.empty else pd.DataFrame()
        st.subheader("Students who selected you")
        if my_students.empty:
            st.info("No students have selected you yet.")
        else:
            st.dataframe(my_students.sort_values(["Subject_Code","Regd_No"]))
            st.download_button("📥 Download my student list (CSV)", data=my_students.to_csv(index=False).encode("utf-8"),
                               file_name=f"{selected_faculty.replace(' ','_')}_students.csv", mime="text/csv")
            st.download_button("📥 Download my student list (Excel)", data=to_excel_bytes(my_students),
                               file_name=f"{selected_faculty.replace(' ','_')}_students.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.subheader("Set / Update your availability for subjects")
        st.write("Mark which subjects you are available to teach/accept students for. This helps Admin see faculty preferences/availability.")

        # Ensure availability initialized for all faculty-subject pairs
        avail_df = load_availability()
        if subjects_df.empty:
            st.warning("Admin must upload subjects.csv first.")
            st.stop()

        my_avail = avail_df[avail_df["Faculty_Name"] == selected_faculty] if not avail_df.empty else pd.DataFrame()
        if my_avail.empty:
            # create defaults
            rows = []
            for _, srow in subjects_df.iterrows():
                rows.append({
                    "Faculty_Name": selected_faculty,
                    "Subject_Code": srow["Subject_Code"],
                    "Subject_Name": srow["Subject_Name"],
                    "Available": "Yes"
                })
            avail_df = pd.concat([avail_df, pd.DataFrame(rows)], ignore_index=True) if not avail_df.empty else pd.DataFrame(rows)
            save_df_to_csv(avail_df, FAC_AVAIL_FILE)
            my_avail = avail_df[avail_df["Faculty_Name"] == selected_faculty]

        # Display and edit availability
        with st.form("availability_form"):
            updated_rows = []
            for _, row in my_avail.iterrows():
                code = row["Subject_Code"]
                sname = row["Subject_Name"]
                current = row.get("Available", "Yes")
                opt = st.selectbox(f"{sname} ({code}) - Available?", ["Yes","No"], index=0 if str(current).strip().lower()=="yes" else 1, key=f"avail_{code}")
                updated_rows.append({
                    "Faculty_Name": selected_faculty,
                    "Subject_Code": code,
                    "Subject_Name": sname,
                    "Available": opt
                })
            save_avail = st.form_submit_button("Save Availability")

        if save_avail:
            # Update avail_df with these rows
            avail_df = load_availability()  # reload to avoid overwriting concurrent changes
            avail_df = avail_df[avail_df["Faculty_Name"] != selected_faculty]
            avail_df = pd.concat([avail_df, pd.DataFrame(updated_rows)], ignore_index=True)
            save_df_to_csv(avail_df, FAC_AVAIL_FILE)
            st.success("✅ Your availability has been updated.")
            st.rerun()

# -----------------------
# STUDENT SECTION
# -----------------------
elif mode == "Student Section":
    st.header("🧑‍🎓 Student: Choose Faculty for Each Subject")

    if subjects_df.empty or faculty_df.empty:
        st.warning("Admin must upload subjects.csv and faculty_list.csv before students can make selections.")
        st.stop()

    with st.form("student_login_form"):
        st.write("Enter your details")
        regd = st.text_input("Registration Number", max_chars=50)
        name = st.text_input("Student Name")
        years = sorted(subjects_df["Year"].dropna().unique().tolist())
        year = st.selectbox("Year", years)
        section = st.text_input("Section (e.g., A)", max_chars=5)

        submit_login = st.form_submit_button("Proceed to select faculties")
    if submit_login:
        if not regd or not name or not year or not section:
            st.error("Please fill all fields to proceed.")
        else:
            # Get subjects for the chosen year
            year_subjects = subjects_df[subjects_df["Year"].astype(str) == str(year)]
            if year_subjects.empty:
                st.warning(f"No subjects found for Year = {year}. Contact admin.")
            else:
                st.success("Subjects loaded. Please select one faculty for each subject below.")
                # Build the selection form
                with st.form("faculty_selection_form"):
                    selections = []
                    # All faculty names (student chooses from all faculty)
                    if "Faculty_Name" in faculty_df.columns:
                        all_faculties = sorted(faculty_df["Faculty_Name"].dropna().unique().tolist())
                    else:
                        all_faculties = sorted(faculty_df.iloc[:,0].dropna().unique().tolist())
                    for idx, row in year_subjects.iterrows():
                        scode = row["Subject_Code"]
                        sname = row["Subject_Name"]
                        # ensure unique key per student per subject so multiple students don't collide
                        unique_key = f"{scode}_{regd}"
                        selected_fac = st.selectbox(f"{sname} ({scode})", all_faculties, key=unique_key)
                        selections.append({"Subject_Code": scode, "Subject_Name": sname, "Faculty_Selected": selected_fac})

                    submit_choices = st.form_submit_button("Submit My Choices")

                if submit_choices:
                    # Reload choices from persistent file
                    df_choices = load_choices()

                    # Remove any existing entries for this student (same regd) for these subject_codes
                    subject_codes = [s["Subject_Code"] for s in selections]
                    if not df_choices.empty:
                        df_choices = df_choices[~((df_choices["Regd_No"] == regd) & (df_choices["Subject_Code"].isin(subject_codes)))]

                    # Append new choices
                    new_rows = []
                    for s in selections:
                        new_rows.append({
                            "Regd_No": regd,
                            "Name": name,
                            "Year": year,
                            "Section": section,
                            "Subject_Code": s["Subject_Code"],
                            "Subject_Name": s["Subject_Name"],
                            "Faculty_Selected": s["Faculty_Selected"]
                        })

                    new_df = pd.DataFrame(new_rows)
                    final_df = pd.concat([df_choices, new_df], ignore_index=True) if not df_choices.empty else new_df
                    save_df_to_csv(final_df, CHOICE_FILE)
                    st.success("✅ Your choices have been recorded.")
                    st.write("You selected:")
                    st.dataframe(new_df)

                    st.info("If you re-submit later with the same Registration Number, your previous selections for these subjects will be replaced.")
                    # refresh so other pages (admin/faculty) see updated data
                    st.rerun()

    # show recent submissions by this student (if exists)
    try:
        if regd:
            df_choices = load_choices()
            if not df_choices.empty:
                my_choices = df_choices[df_choices["Regd_No"] == str(regd)]
                if not my_choices.empty:
                    st.markdown("### Your previous submissions (if any)")
                    st.dataframe(my_choices.sort_values("Subject_Code"))
    except NameError:
        pass
