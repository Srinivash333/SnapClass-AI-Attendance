import streamlit as st
import numpy as np
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from datetime import datetime

from src.ui.base_layout import (
    style_background_dashboard,
    style_base_layout
)

from src.components.header import header_dashboard
from src.components.footer import footer_dashboard
from src.components.subject_card import subject_card

from src.database.db import (
    check_teacher_exists,
    create_teacher,
    teacher_login,
    get_teacher_subjects,
    get_attendance_for_teacher,
    get_enrolled_students_with_profiles,
)

from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog
from src.components.dialog_add_photo import add_photos_dialog
from src.components.dialog_attendance_results import attendance_result_dialog
from src.components.dialog_voice_attendance import voice_attendance_dialog

from src.pipelines.face_pipeline import predict_attendance


# =========================================================
# TEACHER SCREEN
# =========================================================

def teacher_screen():

    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()

    elif (
        "teacher_login_type" not in st.session_state
        or st.session_state.teacher_login_type == "login"
    ):
        teacher_screen_login()

    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()


# =========================================================
# TEACHER DASHBOARD
# =========================================================

def teacher_dashboard():

    teacher_data = st.session_state.teacher_data

    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge"
    )

    with c1:
        header_dashboard()

    with c2:

        st.subheader(
            f"Welcome, {teacher_data['name']}"
        )

        if st.button(
            "Logout",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace"
        ):
            st.session_state["is_logged_in"] = False

            if "teacher_data" in st.session_state:
                del st.session_state.teacher_data

            st.rerun()

    st.space()

    # -----------------------------------------------------
    # DEFAULT TAB
    # -----------------------------------------------------

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = "take_attendance"

    tab1, tab2, tab3 = st.columns(3)

    # -----------------------------------------------------
    # TAKE ATTENDANCE TAB
    # -----------------------------------------------------

    with tab1:

        type1 = (
            "primary"
            if st.session_state.current_teacher_tab == "take_attendance"
            else "tertiary"
        )

        if st.button(
            "Take Attendance",
            type=type1,
            width="stretch",
            icon=":material/ar_on_you:"
        ):
            st.session_state.current_teacher_tab = "take_attendance"
            st.rerun()

    # -----------------------------------------------------
    # MANAGE SUBJECTS TAB
    # -----------------------------------------------------

    with tab2:

        type2 = (
            "primary"
            if st.session_state.current_teacher_tab == "manage_subjects"
            else "tertiary"
        )

        if st.button(
            "Manage Subjects",
            type=type2,
            width="stretch",
            icon=":material/book_ribbon:"
        ):
            st.session_state.current_teacher_tab = "manage_subjects"
            st.rerun()

    # -----------------------------------------------------
    # ATTENDANCE RECORDS TAB
    # -----------------------------------------------------

    with tab3:

        type3 = (
            "primary"
            if st.session_state.current_teacher_tab == "attendance_records"
            else "tertiary"
        )

        if st.button(
            "Attendance Records",
            type=type3,
            width="stretch",
            icon=":material/cards_stack:"
        ):
            st.session_state.current_teacher_tab = "attendance_records"
            st.rerun()

    st.divider()

    # -----------------------------------------------------
    # LOAD SELECTED TAB
    # -----------------------------------------------------

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()

    elif st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()

    elif st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()

    footer_dashboard()


# =========================================================
# TAKE ATTENDANCE
# =========================================================

def clear_attendance_images():
    """Clear photo data and the related Streamlit widgets in one action."""
    had_images = bool(st.session_state.get("attendance_images"))
    st.session_state["attendance_images"] = []
    for widget_key in ("dialog_cam", "dialog_upload", "photo_tab"):
        st.session_state.pop(widget_key, None)
    st.toast(
        "All classroom photos cleared."
        if had_images
        else "There are no classroom photos to clear."
    )

def teacher_tab_take_attendance():

    teacher_id = st.session_state.teacher_data["teacher_id"]

    st.header("Take AI Attendance")

    # -----------------------------------------------------
    # INITIALIZE ATTENDANCE IMAGES
    # -----------------------------------------------------

    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images = []

    # -----------------------------------------------------
    # GET TEACHER SUBJECTS
    # -----------------------------------------------------

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:

        st.warning(
            "You haven't created any subjects yet! "
            "Please create one to begin!"
        )

        return

    # -----------------------------------------------------
    # SUBJECT SELECTION
    # -----------------------------------------------------

    subject_options = {
        f"{s['name']} - {s['subject_code']}": s["subject_id"]
        for s in subjects
    }

    col1, col2 = st.columns(
        [3, 1],
        vertical_alignment="bottom"
    )

    with col1:

        selected_subject_label = st.selectbox(
            "Select Subject",
            options=list(subject_options.keys())
        )

    with col2:

        if st.button(
            "Add Photos",
            type="primary",
            icon=":material/photo_prints:",
            width="stretch"
        ):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    # -----------------------------------------------------
    # DISPLAY ADDED PHOTOS
    # -----------------------------------------------------

    if st.session_state.attendance_images:

        st.header("Added Photos")

        gallery_cols = st.columns(4)

        for idx, img in enumerate(
            st.session_state.attendance_images
        ):

            with gallery_cols[idx % 4]:

                st.image(
                    img,
                    width="stretch",
                    caption=f"Photo {idx + 1}"
                )

    has_photos = bool(
        st.session_state.attendance_images
    )

    c1, c2, c3 = st.columns(3)

    # =====================================================
    # CLEAR PHOTOS
    # =====================================================

    with c1:

        if st.button(
            "Clear all photos",
            width="stretch",
            type="tertiary",
            icon=":material/delete:",
            key="clear_attendance_photos",
            on_click=clear_attendance_images,
        ):
            # The callback performs the reset before this run is rendered.
            pass

    # =====================================================
    # RUN FACE ANALYSIS
    # =====================================================

    with c2:

        if st.button(
            "Run Face Analysis",
            width="stretch",
            type="secondary",
            icon=":material/analytics:",
            key="run_face_analysis",
        ):

            if not has_photos:
                st.warning(
                    "Add at least one classroom photo before running face analysis."
                )
                return

            with st.spinner(
                "Deep scanning classroom photos..."
            ):

                # -------------------------------------------------
                # Store detected students
                # -------------------------------------------------

                all_detected_ids = {}

                # -------------------------------------------------
                # Analyze every uploaded photo
                # -------------------------------------------------

                failed_images = []

                for idx, img in enumerate(
                    st.session_state.attendance_images
                ):

                    try:
                        img_np = np.array(img.convert("RGB"))
                        detected, _, _ = predict_attendance(img_np)
                    except Exception as error:
                        failed_images.append(f"Photo {idx + 1}: {error}")
                        continue

                    if detected:

                        for sid in detected.keys():

                            student_id = int(sid)

                            all_detected_ids.setdefault(
                                student_id,
                                []
                            ).append(
                                f"Photo {idx + 1}"
                            )

                if failed_images:
                    st.warning(
                        "Some photos could not be analyzed: "
                        + "; ".join(failed_images)
                    )

                if len(failed_images) == len(st.session_state.attendance_images):
                    st.error("Face analysis could not process any of the selected photos.")
                    return

                # -------------------------------------------------
                # Get students enrolled in selected subject
                # -------------------------------------------------

                try:
                    enrolled_students = get_enrolled_students_with_profiles(selected_subject_id)
                except Exception as error:
                    st.error(f"Could not load students for this subject: {error}")
                    return

                # -------------------------------------------------
                # IMPORTANT FIX
                #
                # Check enrollment BEFORE using results
                # -------------------------------------------------

                if not enrolled_students:

                    st.warning(
                        "No students enrolled in this course."
                    )

                else:

                    # Initialize these variables BEFORE the loop
                    results = []
                    attendance_to_log = []

                    current_timestamp = (
                        datetime.now()
                        .strftime("%Y-%m-%dT%H:%M:%S")
                    )

                    # -------------------------------------------------
                    # Generate attendance result
                    # -------------------------------------------------

                    for node in enrolled_students:

                        student = node.get("students")

                        if not student:
                            continue

                        student_id = int(
                            student["student_id"]
                        )

                        sources = all_detected_ids.get(
                            student_id,
                            []
                        )

                        is_present = len(sources) > 0

                        # ---------------------------------------------
                        # Result shown in dialog
                        # ---------------------------------------------

                        results.append(
                            {
                                "Name": student["name"],
                                "ID": student_id,
                                "Source": (
                                    ", ".join(sources)
                                    if is_present
                                    else "-"
                                ),
                                "Status": (
                                    "✅ Present"
                                    if is_present
                                    else "❌ Absent"
                                )
                            }
                        )

                        # ---------------------------------------------
                        # Attendance record to save
                        # ---------------------------------------------

                        attendance_to_log.append(
                            {
                                "student_id": student_id,
                                "subject_id": selected_subject_id,
                                "timestamp": current_timestamp,
                                "is_present": bool(is_present)
                            }
                        )

                    # -------------------------------------------------
                    # Show attendance results ONLY if we have results
                    # -------------------------------------------------

                    if results:

                        attendance_result_dialog(
                            pd.DataFrame(results),
                            attendance_to_log
                        )

                    else:

                        st.warning(
                            "No valid student records were found "
                            "for this subject."
                        )

    # =====================================================
    # VOICE ATTENDANCE
    # =====================================================

    with c3:

        if st.button(
            "Use Voice Attendance",
            type="primary",
            width="stretch",
            icon=":material/mic:"
        ):

            voice_attendance_dialog(
                selected_subject_id
            )


# =========================================================
# MANAGE SUBJECTS
# =========================================================

def teacher_tab_manage_subjects():

    teacher_id = st.session_state.teacher_data[
        "teacher_id"
    ]

    col1, col2 = st.columns(2)

    with col1:

        st.header(
            "Manage Subjects",
            width="stretch"
        )

    with col2:

        if st.button(
            "Create New Subject",
            width="stretch"
        ):

            create_subject_dialog(
                teacher_id
            )

    # -----------------------------------------------------
    # GET SUBJECTS
    # -----------------------------------------------------

    subjects = get_teacher_subjects(
        teacher_id
    )

    if subjects:

        for sub in subjects:

            stats = [
                (
                    "🫂",
                    "Students",
                    sub["total_students"]
                ),
                (
                    "🕰️",
                    "Classes",
                    sub["total_classes"]
                )
            ]

            # -------------------------------------------------
            # Share button callback
            # -------------------------------------------------

            def share_btn(
                subject_name=sub["name"],
                subject_code=sub["subject_code"]
            ):

                if st.button(
                    f"Share Code: {subject_name}",
                    key=f"share_{subject_code}",
                    icon=":material/share:"
                ):

                    share_subject_dialog(
                        subject_name,
                        subject_code
                    )

                st.space()

            subject_card(
                name=sub["name"],
                code=sub["subject_code"],
                section=sub["section"],
                stats=stats,
                footer_callback=share_btn
            )

    else:

        st.info(
            "NO SUBJECTS FOUND. CREATE ONE ABOVE"
        )


# =========================================================
# ATTENDANCE RECORDS
# =========================================================

def build_attendance_excel(session_rows, session):
    """Build a shareable Excel file for one attendance session."""
    export_df = session_rows[
        ["Student ID", "Student", "Attendance Status"]
    ].copy()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        export_df.to_excel(
            writer,
            sheet_name="Attendance",
            index=False,
            startrow=4,
        )

        workbook = writer.book
        worksheet = writer.sheets["Attendance"]
        title_format = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "font_color": "#172554",
        })
        detail_format = workbook.add_format({
            "font_color": "#475569",
        })
        header_format = workbook.add_format({
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#4F5EE8",
            "border": 0,
        })

        worksheet.write("A1", "Attendance report", title_format)
        worksheet.write("A2", f"Subject: {session['Subject']} ({session['Subject Code']})", detail_format)
        worksheet.write("A3", f"Session: {session['Time']}", detail_format)
        for col_num, column_name in enumerate(export_df.columns):
            worksheet.write(4, col_num, column_name, header_format)

        worksheet.set_column("A:A", 14)
        worksheet.set_column("B:B", 28)
        worksheet.set_column("C:C", 20)
        worksheet.freeze_panes(5, 0)
        worksheet.autofilter(4, 0, 4 + len(export_df), len(export_df.columns) - 1)

    return output.getvalue()


def build_attendance_pdf(session_rows, session):
    """Build a compact, ready-to-share PDF for one attendance session."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.textColor = colors.HexColor("#172554")
    detail_style = styles["BodyText"]
    detail_style.textColor = colors.HexColor("#475569")

    table_rows = [["Student ID", "Student", "Status"]]
    for _, student in session_rows.iterrows():
        table_rows.append([
            str(student["Student ID"]),
            str(student["Student"]),
            str(student["Attendance Status"]),
        ])

    attendance_table = Table(
        table_rows,
        colWidths=[1.15 * inch, 3.25 * inch, 1.25 * inch],
        repeatRows=1,
    )
    attendance_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F5EE8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    document.build([
        Paragraph("Attendance report", title_style),
        Spacer(1, 0.14 * inch),
        Paragraph(f"Subject: {session['Subject']} ({session['Subject Code']})", detail_style),
        Paragraph(f"Session: {session['Time']}", detail_style),
        Spacer(1, 0.22 * inch),
        attendance_table,
    ])
    return output.getvalue()

def teacher_tab_attendance_records():

    st.header("Attendance Records")

    teacher_id = st.session_state.teacher_data[
        "teacher_id"
    ]

    try:
        records = get_attendance_for_teacher(teacher_id)
    except Exception as error:
        st.error(f"Could not load attendance records: {error}")
        return

    if not records:

        st.info(
            "No attendance records found."
        )

        return

    data = []

    # -----------------------------------------------------
    # Prepare attendance data
    # -----------------------------------------------------

    for r in records:

        ts = r.get("timestamp")

        if ts:

            try:

                formatted_time = (
                    datetime
                    .fromisoformat(ts)
                    .strftime("%Y-%m-%d %I:%M %p")
                )

            except ValueError:

                formatted_time = ts

            ts_group = ts.split(".")[0]

        else:

            formatted_time = "N/A"
            ts_group = None

        subject = r.get("subjects") or {}
        student = r.get("students") or {}

        data.append(
            {
                "ts_group": ts_group,
                "Time": formatted_time,
                "Subject": subject.get(
                    "name",
                    "Unknown"
                ),
                "Subject Code": subject.get(
                    "subject_code",
                    "N/A"
                ),
                "Student ID": student.get("student_id", r.get("student_id", "N/A")),
                "Student": student.get("name", "Unknown student"),
                "is_present": bool(
                    r.get(
                        "is_present",
                        False
                    )
                )
            }
        )

    if not data:

        st.info(
            "No attendance records found."
        )

        return

    df = pd.DataFrame(data)

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    summary = (
        df
        .groupby(
            [
                "ts_group",
                "Time",
                "Subject",
                "Subject Code"
            ]
        )
        .agg(
            Present_Count=(
                "is_present",
                "sum"
            ),
            Total_Count=(
                "is_present",
                "count"
            )
        )
        .reset_index()
    )

    # -----------------------------------------------------
    # Attendance stats
    # -----------------------------------------------------

    summary["Attendance Stats"] = (
        "✅ "
        + summary["Present_Count"].astype(str)
        + " / "
        + summary["Total_Count"].astype(str)
        + " Students"
    )

    summary = summary.sort_values(by="ts_group", ascending=False)

    # -----------------------------------------------------
    # Display each session with its own shareable Excel export.
    # -----------------------------------------------------
    headings = st.columns([1.45, 1.05, 1.05, 1.25, 0.85, 0.85])
    for column, label in zip(
        headings,
        ["Time", "Subject", "Subject Code", "Attendance Stats", "Format", "Export"],
    ):
        column.caption(label)

    for row_index, session in summary.iterrows():
        session_rows = df[
            (df["ts_group"] == session["ts_group"])
            & (df["Subject"] == session["Subject"])
            & (df["Subject Code"] == session["Subject Code"])
        ].copy()
        session_rows["Attendance Status"] = session_rows["is_present"].map(
            {True: "Present", False: "Absent"}
        )
        file_timestamp = str(session["ts_group"] or "attendance").replace(":", "-")
        filename = f"attendance_{session['Subject Code']}_{file_timestamp}.xlsx"

        with st.container(border=True):
            columns = st.columns([1.45, 1.05, 1.05, 1.25, 0.85, 0.85], vertical_alignment="center")
            columns[0].write(session["Time"])
            columns[1].write(session["Subject"])
            columns[2].write(session["Subject Code"])
            columns[3].write(session["Attendance Stats"])
            export_format = columns[4].selectbox(
                "Export format",
                ["Excel", "PDF"],
                label_visibility="collapsed",
                key=f"attendance_format_{row_index}",
            )
            if export_format == "PDF":
                export_data = build_attendance_pdf(session_rows, session)
                filename = filename.replace(".xlsx", ".pdf")
                mime_type = "application/pdf"
            else:
                export_data = build_attendance_excel(session_rows, session)
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            columns[5].download_button(
                "Download",
                data=export_data,
                file_name=filename,
                mime=mime_type,
                icon=":material/download:",
                key=f"attendance_export_{row_index}",
            )


# =========================================================
# TEACHER LOGIN
# =========================================================

def login_teacher(username, password):

    if not username or not password:
        return False

    teacher = teacher_login(
        username,
        password
    )

    if teacher:

        st.session_state.user_role = "teacher"

        st.session_state.teacher_data = teacher

        st.session_state.is_logged_in = True

        return True

    return False


# =========================================================
# TEACHER LOGIN SCREEN
# =========================================================

def teacher_screen_login():

    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge"
    )

    with c1:

        header_dashboard()

    with c2:

        if st.button(
            "Go back to Home",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace"
        ):

            st.session_state["login_type"] = None

            st.rerun()

    st.header(
        "Login using password",
        text_alignment="center"
    )

    st.space()
    st.space()

    teacher_username = st.text_input(
        "Enter username",
        placeholder="Eg-Ravi"
    )

    teacher_pass = st.text_input(
        "Enter password",
        type="password",
        placeholder="Ravi@123"
    )

    st.divider()

    btnc1, btnc2 = st.columns(2)

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with btnc1:

        if st.button(
            "Login",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch"
        ):

            if login_teacher(
                teacher_username,
                teacher_pass
            ):

                st.toast(
                    "Welcome back!",
                    icon="👋"
                )

                import time
                time.sleep(1)

                st.rerun()

            else:

                st.error(
                    "Invalid username and password combo"
                )

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    with btnc2:

        if st.button(
            "Register Instead",
            type="primary",
            icon=":material/passkey:",
            width="stretch"
        ):

            st.session_state.teacher_login_type = "register"

            st.rerun()

    footer_dashboard()


# =========================================================
# REGISTER TEACHER
# =========================================================

def register_teacher(
    teacher_username,
    teacher_name,
    teacher_pass,
    teacher_pass_confirm
):

    # -----------------------------------------------------
    # Validate fields
    # -----------------------------------------------------

    if (
        not teacher_username
        or not teacher_name
        or not teacher_pass
    ):

        return False, "All fields are required!"

    # -----------------------------------------------------
    # Check username
    # -----------------------------------------------------

    if check_teacher_exists(
        teacher_username
    ):

        return False, "Username already taken"

    # -----------------------------------------------------
    # Confirm password
    # -----------------------------------------------------

    if teacher_pass != teacher_pass_confirm:

        return False, "Passwords don't match"

    # -----------------------------------------------------
    # Create teacher
    # -----------------------------------------------------

    try:

        create_teacher(
            teacher_username,
            teacher_pass,
            teacher_name
        )

        return True, "Successfully Created! Login Now"

    except Exception as e:

        print(
            "Teacher registration error:",
            e
        )

        return False, "Unexpected Error!"


# =========================================================
# TEACHER REGISTRATION SCREEN
# =========================================================

def teacher_screen_register():

    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge"
    )

    with c1:

        header_dashboard()

    with c2:

        if st.button(
            "Go back to Home",
            type="secondary",
            key="loginbackbtn",
            shortcut="control+backspace"
        ):

            st.session_state["login_type"] = None

            st.rerun()

    st.header(
        "Register your teacher profile"
    )

    st.space()
    st.space()

    teacher_username = st.text_input(
        "Enter username",
        placeholder="Eg-Ravi"
    )

    teacher_name = st.text_input(
        "Enter name",
        placeholder="Eg-Ravi Pujar"
    )

    teacher_pass = st.text_input(
        "Enter password",
        type="password",
        placeholder="Ravi@123"
    )

    teacher_pass_confirm = st.text_input(
        "Confirm your password",
        type="password",
        placeholder="Ravi@123"
    )

    st.divider()

    btnc1, btnc2 = st.columns(2)

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    with btnc1:

        if st.button(
            "Register now",
            icon=":material/passkey:",
            shortcut="control+enter",
            width="stretch"
        ):

            success, message = register_teacher(
                teacher_username,
                teacher_name,
                teacher_pass,
                teacher_pass_confirm
            )

            if success:

                st.success(message)

                import time
                time.sleep(2)

                st.session_state.teacher_login_type = "login"

                st.rerun()

            else:

                st.error(message)

    # -----------------------------------------------------
    # LOGIN INSTEAD
    # -----------------------------------------------------

    with btnc2:

        if st.button(
            "Login Instead",
            type="primary",
            icon=":material/passkey:",
            width="stretch"
        ):

            st.session_state.teacher_login_type = "login"

            st.rerun()

    footer_dashboard()
