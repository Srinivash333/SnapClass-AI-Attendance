# 📸 SnapClass - AI-Powered Attendance System

**SnapClass** is a modern, fast, and intelligent attendance management application built with **Streamlit**, **Python**, and **MongoDB**. It automates classroom attendance using multi-modal AI — including **Face Recognition** from group photos and **Voice Recognition** from audio recordings.

---

## ✨ Features

### 👩‍🏫 Teacher Portal
- **Dashboard & Class Management**: Create subjects, manage sections, and view total enrolled students and class sessions.
- **Class Join QR & Links**: Generate instant QR codes and shareable links with subject join codes for quick student enrollment.
- **Photo Attendance (Face Recognition)**: Upload or capture classroom photos. SnapClass detects and matches faces using trained SVM classifiers to automatically mark attendance.
- **Voice Attendance (Voice Recognition)**: Record classroom audio where students state "I am present". SnapClass segments audio and matches voice embeddings using Resemblyzer.
- **Attendance Records & Export**: View session logs and export attendance reports to styled **Excel** (`.xlsx`) or **PDF** (`.pdf`) formats.

### 🧑‍🎓 Student Portal
- **Subject Enrollment**: Join courses using subject codes or direct QR code join links.
- **Biometric Registration**:
  - **Face Profile**: Capture photos to register 128-dimensional face descriptors.
  - **Voice Profile**: Record audio samples to create voice embeddings for speaker verification.
- **Attendance Tracking**: View enrolled subjects and personal attendance percentage breakdown.

---

## 🛠️ Technology Stack

- **Frontend / App Framework**: [Streamlit](https://streamlit.io/)
- **Database Layer**: [MongoDB](https://www.mongodb.com/) via [PyMongo](https://pymongo.readthedocs.io/)
- **Face Recognition Pipeline**: `dlib`, `face-recognition-models`, `scikit-learn` (Support Vector Classifier)
- **Voice Recognition Pipeline**: `resemblyzer`, `librosa`, `webrtcvad-wheels`
- **Security**: `bcrypt` password hashing
- **Report Generation**: `reportlab` (PDF), `xlsxwriter` (Excel)
- **QR Generation**: `segno`

---

## 📁 Project Structure

```
fast_Attendence/
├── app.py                          # Streamlit application main entrypoint
├── requirements.txt                # Python package dependencies
├── .streamlit/
│   └── secrets.toml                # Application & database secrets
├── src/
│   ├── components/                 # UI Dialogs & reusable widgets
│   │   ├── dialog_add_photo.py     # Camera & photo upload dialog
│   │   ├── dialog_attendance_results.py # Attendance confirmation view
│   │   ├── dialog_auto_enroll.py   # Quick QR join dialog
│   │   ├── dialog_create_subject.py# New subject modal
│   │   ├── dialog_enroll.py        # Manual subject enrollment modal
│   │   ├── dialog_share_subject.py # QR code & share link generator
│   │   └── dialog_voice_attendance.py # Audio recording & processing modal
│   ├── database/                   # MongoDB configuration & data operations
│   │   ├── config.py               # PyMongo connection & index creation
│   │   └── db.py                   # CRUD operations for teachers, students, subjects, attendance
│   ├── pipelines/                  # AI ML Recognition pipelines
│   │   ├── face_pipeline.py        # Dlib face feature extraction & SVM classifier
│   │   └── voice_pipeline.py       # Resemblyzer voice embedding generator & matcher
│   ├── screens/                    # Main app views
│   │   ├── home_screen.py          # Portal selection landing page
│   │   ├── student_screen.py       # Student dashboard & biometric registration
│   │   └── teacher_screen.py       # Teacher dashboard, attendance taking, & reports
│   └── ui/                         # Base layout and custom CSS styling
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.11** installed on your system.
- A running **MongoDB** instance (local MongoDB Server or [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)).

### 2. Environment Setup

Clone or navigate to the project directory and create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment:

- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Database Credentials

Configure your MongoDB connection string in `.streamlit/secrets.toml`:

```toml
MONGO_URI = "mongodb://localhost:27017" # or your MongoDB Atlas connection string
MONGO_DB_NAME = "fast_attendence"
```

### 5. Run the Application

Launch the Streamlit web application:

```bash
streamlit run app.py
```

The application will open automatically in your browser at `http://localhost:8501`.

---

## 🗄️ Database Collections

The application automatically initializes indexes on startup for optimal query performance across the following MongoDB collections:

- `teachers`: Holds teacher login credentials (`username`, hashed `password`, `name`).
- `students`: Stores student profiles and biometric vectors (`student_id`, `face_embedding`, `voice_embedding`).
- `subjects`: Stores course metadata (`subject_code`, `name`, `section`, `teacher_id`).
- `subject_students`: Junction collection tracking student course enrollments.
- `attendance_logs`: Stores attendance logs (`student_id`, `subject_id`, `timestamp`, `is_present`).

---


