import streamlit as st
from pymongo import MongoClient, ASCENDING


@st.cache_resource
def get_mongo_client():
    mongo_uri = st.secrets.get("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri)
    return client


@st.cache_resource
def get_database():
    client = get_mongo_client()
    db_name = st.secrets.get("MONGO_DB_NAME", "fast_attendence")
    database = client[db_name]

    # Create indexes for frequently queried fields
    try:
        database["teachers"].create_index([("username", ASCENDING)], unique=True)
        database["students"].create_index([("student_id", ASCENDING)], unique=True)
        database["subjects"].create_index([("subject_code", ASCENDING)], unique=True)
        database["subjects"].create_index([("teacher_id", ASCENDING)])
        database["subject_students"].create_index(
            [("subject_id", ASCENDING), ("student_id", ASCENDING)], unique=True
        )
        database["subject_students"].create_index([("student_id", ASCENDING)])
        database["subject_students"].create_index([("subject_id", ASCENDING)])
        database["attendance_logs"].create_index([("student_id", ASCENDING)])
        database["attendance_logs"].create_index([("subject_id", ASCENDING)])
        database["attendance_logs"].create_index([("timestamp", ASCENDING)])
    except Exception:
        pass

    return database


db = get_database()
teachers_col = db["teachers"]
students_col = db["students"]
subjects_col = db["subjects"]
subject_students_col = db["subject_students"]
attendance_logs_col = db["attendance_logs"]