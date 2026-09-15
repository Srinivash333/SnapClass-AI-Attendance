
import time

import numpy as np
import streamlit as st
from PIL import Image

from src.ui.base_layout import (
    style_background_dashboard,
    style_base_layout,
)

from src.components.header import header_dashboard
from src.components.footer import footer_dashboard
from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card

from src.pipelines.face_pipeline import (
    predict_attendance,
    get_face_embeddings,
    train_classifier,
)

from src.pipelines.voice_pipeline import get_voice_embedding

from src.database.db import (
    get_all_students,
    create_student,
    get_student_subjects,
    get_student_attendance,
    unenroll_student_to_subject,
)


def student_dashboard():
    """
    Display the logged-in student's dashboard.
    """

    # Make sure student data exists
    if "student_data" not in st.session_state:
        st.warning("Student session not found.")
        st.rerun()

    student_data = st.session_state.student_data
    student_id = student_data["student_id"]

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------
    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge",
    )

    with c1:
        header_dashboard()

    with c2:
        st.subheader(f"Welcome, {student_data['name']}")

        if st.button(
            "Logout",
            type="secondary",
            key="student_logout_btn",
            shortcut="control+backspace",
        ):
            st.session_state["is_logged_in"] = False
            st.session_state["user_role"] = None

            if "student_data" in st.session_state:
                del st.session_state["student_data"]

            st.rerun()

    st.space()

    # ---------------------------------------------------------
    # SUBJECT HEADER
    # ---------------------------------------------------------
    c1, c2 = st.columns(2)

    with c1:
        st.header("Your Enrolled Subjects")

    with c2:
        if st.button(
            "Enroll in Subject",
            type="primary",
            width="stretch",
            key="enroll_subject_btn",
        ):
            enroll_dialog()

    st.divider()

    # ---------------------------------------------------------
    # LOAD SUBJECTS AND ATTENDANCE
    # ---------------------------------------------------------
    with st.spinner("Loading your enrolled subjects..."):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    # Handle None values safely
    if subjects is None:
        subjects = []

    if logs is None:
        logs = []

    # ---------------------------------------------------------
    # CREATE ATTENDANCE STATISTICS
    # ---------------------------------------------------------
    stats_map = {}

    for log in logs:
        sid = log.get("subject_id")

        if sid is None:
            continue

        if sid not in stats_map:
            stats_map[sid] = {
                "total": 0,
                "attended": 0,
            }

        stats_map[sid]["total"] += 1

        if log.get("is_present"):
            stats_map[sid]["attended"] += 1

    # ---------------------------------------------------------
    # DISPLAY SUBJECTS
    # ---------------------------------------------------------
    if not subjects:
        st.info("You are not enrolled in any subjects yet.")
    else:
        cols = st.columns(2)

        for i, sub_node in enumerate(subjects):

            # Database relationship may return:
            # {"subjects": {...}}
            sub = sub_node.get("subjects")

            if not sub:
                continue

            sid = sub.get("subject_id")

            if sid is None:
                continue

            stats = stats_map.get(
                sid,
                {
                    "total": 0,
                    "attended": 0,
                },
            )

            # -------------------------------------------------
            # UNIQUE UNENROLL FUNCTION
            # -------------------------------------------------
            # IMPORTANT:
            # Each subject gets its own unique button key.
            # This fixes StreamlitDuplicateElementId.
            # -------------------------------------------------
            def unenroll_button(
                current_student_id=student_id,
                current_subject_id=sid,
                current_subject_name=sub["name"],
            ):
                if st.button(
                    "Unenroll from this course",
                    type="tertiary",
                    width="stretch",
                    icon=":material/delete_forever:",
                    key=f"unenroll_{current_subject_id}",
                ):
                    try:
                        with st.spinner("Unenrolling..."):

                            unenroll_student_to_subject(
                                current_student_id,
                                current_subject_id,
                            )

                        st.toast(
                            f"Unenrolled from "
                            f"{current_subject_name} successfully!"
                        )

                        time.sleep(0.5)
                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"Failed to unenroll from "
                            f"{current_subject_name}: {e}"
                        )

            # -------------------------------------------------
            # SUBJECT CARD
            # -------------------------------------------------
            with cols[i % 2]:
                subject_card(
                    name=sub["name"],
                    code=sub["subject_code"],
                    section=sub["section"],
                    stats=[
                        ("📅", "Total", stats["total"]),
                        ("✅", "Attended", stats["attended"]),
                    ],
                    footer_callback=unenroll_button,
                )

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------
    footer_dashboard()


def student_screen():
    """
    Student login / registration screen.
    """

    # ---------------------------------------------------------
    # PAGE STYLING
    # ---------------------------------------------------------
    style_background_dashboard()
    style_base_layout()

    # ---------------------------------------------------------
    # IF ALREADY LOGGED IN
    # ---------------------------------------------------------
    if "student_data" in st.session_state:
        student_dashboard()
        return

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------
    c1, c2 = st.columns(
        2,
        vertical_alignment="center",
        gap="xxlarge",
    )

    with c1:
        header_dashboard()

    with c2:
        if st.button(
            "Go back to Home",
            type="secondary",
            key="student_home_btn",
            shortcut="control+backspace",
        ):
            st.session_state["login_type"] = None
            st.rerun()

    # ---------------------------------------------------------
    # FACE LOGIN
    # ---------------------------------------------------------
    st.header(
        "Login using FaceID",
        text_alignment="center",
    )

    st.space()
    st.space()

    show_registration = False
    photo_source = st.camera_input(
        "Position your face in the center"
    )

    # ---------------------------------------------------------
    # FACE DETECTION
    # ---------------------------------------------------------
    if photo_source:

        img = np.array(Image.open(photo_source))

        with st.spinner("AI is scanning..."):

            try:
                detected, all_ids, num_faces = predict_attendance(img)

            except Exception as e:
                st.error(
                    f"Face recognition failed: {e}"
                )
                return

        # No face
        if num_faces == 0:
            st.warning("Face not found!")

        # Multiple faces
        elif num_faces > 1:
            st.warning("Multiple faces found. Please keep only one face in the camera.")

        # Exactly one face
        else:

            # -------------------------------------------------
            # FACE RECOGNIZED
            # -------------------------------------------------
            if detected:

                student_id = list(detected.keys())[0]

                all_students = get_all_students()

                if all_students is None:
                    all_students = []

                student = next(
                    (
                        s
                        for s in all_students
                        if s.get("student_id") == student_id
                    ),
                    None,
                )

                if student:

                    st.session_state["is_logged_in"] = True
                    st.session_state["user_role"] = "student"
                    st.session_state["student_data"] = student

                    st.toast(
                        f"Welcome back {student['name']}!"
                    )

                    time.sleep(1)
                    st.rerun()

                else:
                    st.error(
                        "Face recognized, but student record was not found."
                    )

            # -------------------------------------------------
            # FACE NOT RECOGNIZED
            # -------------------------------------------------
            else:

                st.info(
                    "Face not recognized! "
                    "You might be a new student."
                )

                show_registration = True

    # ---------------------------------------------------------
    # NEW STUDENT REGISTRATION
    # ---------------------------------------------------------
    if show_registration:

        with st.container(border=True):

            st.header("Register New Profile")

            new_name = st.text_input(
                "Enter your name",
                placeholder="Eg-Ravi",
                key="new_student_name",
            )

            st.subheader("Optional: Voice Enrollment")

            st.info(
                "Enroll your voice for voice-only attendance."
            )

            audio_data = None

            try:
                audio_data = st.audio_input(
                    "Record a short phrase like "
                    "'I am present, my name is Akash.'",
                    key="student_voice_input",
                )

            except Exception:
                st.error(
                    "Audio data capture failed!"
                )

            # -------------------------------------------------
            # CREATE ACCOUNT
            # -------------------------------------------------
            if st.button(
                "Create Account",
                type="primary",
                key="create_student_account_btn",
            ):

                # Check name
                if not new_name.strip():
                    st.warning(
                        "Please enter your name!"
                    )

                else:

                    with st.spinner(
                        "Creating profile..."
                    ):

                        # -------------------------------------
                        # GET FACE EMBEDDING
                        # -------------------------------------
                        try:

                            img = np.array(
                                Image.open(photo_source)
                            )

                            encodings = get_face_embeddings(
                                img
                            )

                        except Exception as e:

                            st.error(
                                f"Could not process your face: {e}"
                            )

                            return

                        # -------------------------------------
                        # FACE EMBEDDING FOUND
                        # -------------------------------------
                        if encodings:

                            face_emb = encodings[0].tolist()

                            # ---------------------------------
                            # VOICE EMBEDDING
                            # ---------------------------------
                            voice_emb = None

                            if audio_data:

                                try:

                                    voice_emb = get_voice_embedding(
                                        audio_data.read()
                                    )

                                except Exception as e:

                                    st.warning(
                                        f"Voice enrollment failed: {e}"
                                    )

                                    voice_emb = None

                            # ---------------------------------
                            # CREATE STUDENT
                            # ---------------------------------
                            try:

                                response_data = create_student(
                                    new_name.strip(),
                                    face_embedding=face_emb,
                                    voice_embedding=voice_emb,
                                )

                            except Exception as e:

                                st.error(
                                    f"Failed to create profile: {e}"
                                )

                                return

                            # ---------------------------------
                            # PROFILE CREATED
                            # ---------------------------------
                            if response_data:

                                # Retrain face classifier
                                try:
                                    train_classifier()
                                except Exception as e:
                                    st.warning(
                                        f"Classifier training failed: {e}"
                                    )

                                # Get created student
                                created_student = response_data[0]

                                st.session_state[
                                    "is_logged_in"
                                ] = True

                                st.session_state[
                                    "user_role"
                                ] = "student"

                                st.session_state[
                                    "student_data"
                                ] = created_student

                                st.toast(
                                    f"Profile Created! "
                                    f"Hi {new_name.strip()}!"
                                )

                                time.sleep(1)
                                st.rerun()

                            else:

                                st.error(
                                    "Failed to create student profile."
                                )

                        # -------------------------------------
                        # FACE EMBEDDING NOT FOUND
                        # -------------------------------------
                        else:

                            st.error(
                                "Couldn't capture your facial "
                                "features for registration."
                            )

    # ---------------------------------------------------------
    # FOOTER
    # ---------------------------------------------------------
    footer_dashboard()

