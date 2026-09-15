from src.database.config import (
    teachers_col,
    students_col,
    subjects_col,
    subject_students_col,
    attendance_logs_col,
)
import bcrypt


def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def check_teacher_exists(username):
    # Check for unique username, returns True when username is already taken
    doc = teachers_col.find_one({"username": username})
    return doc is not None


def create_teacher(username, password, name):
    data = {
        "teacher_id": username,
        "username": username,
        "password": hash_pass(password),
        "name": name,
    }
    teachers_col.insert_one(data)
    doc = dict(data)
    doc.pop("_id", None)
    return [doc]


def teacher_login(username, password):
    teacher = teachers_col.find_one({"username": username})
    if teacher:
        if check_pass(password, teacher["password"]):
            teacher_doc = dict(teacher)
            teacher_doc["teacher_id"] = teacher_doc.get("teacher_id", teacher_doc["username"])
            teacher_doc.pop("_id", None)
            return teacher_doc
    return None


def get_all_students():
    return list(students_col.find({}, {"_id": 0}))


def create_student(new_name, face_embedding=None, voice_embedding=None):
    # Generate integer student_id for classifier compatibility
    last_student = students_col.find_one(sort=[("student_id", -1)])
    next_id = 1001
    if last_student and "student_id" in last_student:
        try:
            next_id = int(last_student["student_id"]) + 1
        except (ValueError, TypeError):
            next_id = 1001

    data = {
        "student_id": next_id,
        "name": new_name,
        "face_embedding": face_embedding,
        "voice_embedding": voice_embedding,
    }
    students_col.insert_one(data)
    doc = dict(data)
    doc.pop("_id", None)
    return [doc]


def create_subject(subject_code, name, section, teacher_id):
    data = {
        "subject_id": subject_code,
        "subject_code": subject_code,
        "name": name,
        "section": section,
        "teacher_id": teacher_id,
    }
    subjects_col.insert_one(data)
    doc = dict(data)
    doc.pop("_id", None)
    return [doc]


def get_teacher_subjects(teacher_id):
    subjects = list(subjects_col.find({"teacher_id": teacher_id}, {"_id": 0}))

    for sub in subjects:
        sid = sub.get("subject_id")
        sub["total_students"] = subject_students_col.count_documents({"subject_id": sid})
        attendance = list(attendance_logs_col.find({"subject_id": sid}, {"timestamp": 1, "_id": 0}))
        unique_sessions = len(set(log["timestamp"] for log in attendance if "timestamp" in log))
        sub["total_classes"] = unique_sessions

    return subjects


def enroll_student_to_subject(student_id, subject_id):
    try:
        student_id_val = int(student_id)
    except (ValueError, TypeError):
        student_id_val = student_id

    data = {"student_id": student_id_val, "subject_id": str(subject_id)}
    subject_students_col.update_one(
        {"student_id": student_id_val, "subject_id": str(subject_id)},
        {"$set": data},
        upsert=True,
    )
    return [data]


def unenroll_student_to_subject(student_id, subject_id):
    try:
        student_id_val = int(student_id)
    except (ValueError, TypeError):
        student_id_val = student_id

    subject_students_col.delete_many(
        {"student_id": student_id_val, "subject_id": str(subject_id)}
    )
    return [{"student_id": student_id_val, "subject_id": str(subject_id)}]


def get_student_subjects(student_id):
    try:
        student_id_val = int(student_id)
    except (ValueError, TypeError):
        student_id_val = student_id

    enrollments = list(subject_students_col.find({"student_id": student_id_val}, {"_id": 0}))
    result = []
    for enr in enrollments:
        sub_doc = subjects_col.find_one({"subject_id": enr["subject_id"]}, {"_id": 0})
        if sub_doc:
            result.append({
                "student_id": enr["student_id"],
                "subject_id": enr["subject_id"],
                "subjects": sub_doc,
            })
    return result


def get_student_attendance(student_id):
    try:
        student_id_val = int(student_id)
    except (ValueError, TypeError):
        student_id_val = student_id

    logs = list(attendance_logs_col.find({"student_id": student_id_val}, {"_id": 0}))
    result = []
    for log in logs:
        sub_doc = subjects_col.find_one({"subject_id": log["subject_id"]}, {"_id": 0})
        log_entry = dict(log)
        log_entry["subjects"] = sub_doc or {}
        result.append(log_entry)
    return result


def create_attendance(logs):
    if not logs:
        raise ValueError("No attendance entries were generated to save.")

    cleaned_logs = []
    for log in logs:
        entry = dict(log)
        if "student_id" in entry:
            try:
                entry["student_id"] = int(entry["student_id"])
            except (ValueError, TypeError):
                pass
        entry.pop("_id", None)
        cleaned_logs.append(entry)

    res = attendance_logs_col.insert_many(cleaned_logs)
    if not res.inserted_ids:
        raise RuntimeError("MongoDB did not confirm that attendance was saved.")
    return cleaned_logs


def get_attendance_for_teacher(teacher_id):
    teacher_subjects = list(subjects_col.find({"teacher_id": teacher_id}, {"_id": 0}))
    subject_map = {s["subject_id"]: s for s in teacher_subjects}

    if not subject_map:
        return []

    subject_ids = list(subject_map.keys())
    logs = list(
        attendance_logs_col.find(
            {"subject_id": {"$in": subject_ids}},
            {"_id": 0}
        ).sort("timestamp", -1)
    )

    result = []
    for log in logs:
        sid = log.get("subject_id")
        st_id = log.get("student_id")

        student_doc = students_col.find_one(
            {"student_id": st_id},
            {"_id": 0, "student_id": 1, "name": 1}
        )

        log_entry = dict(log)
        log_entry["subjects"] = subject_map.get(sid, {})
        log_entry["students"] = student_doc or {"student_id": st_id, "name": "Unknown student"}
        result.append(log_entry)

    return result


def get_subject_by_code(subject_code):
    return subjects_col.find_one({"subject_code": subject_code}, {"_id": 0})


def check_student_enrolled(subject_id, student_id):
    try:
        student_id_val = int(student_id)
    except (ValueError, TypeError):
        student_id_val = student_id

    enr = subject_students_col.find_one(
        {"subject_id": str(subject_id), "student_id": student_id_val}
    )
    return enr is not None


def get_enrolled_students_with_profiles(subject_id):
    enrollments = list(
        subject_students_col.find({"subject_id": str(subject_id)}, {"_id": 0})
    )
    result = []
    for enr in enrollments:
        st_id = enr.get("student_id")
        student_doc = students_col.find_one({"student_id": st_id}, {"_id": 0})
        if student_doc:
            result.append({
                "student_id": enr["student_id"],
                "subject_id": enr["subject_id"],
                "students": student_doc,
            })
    return result


