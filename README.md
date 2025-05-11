# 🧰 NextHire API

A **FastAPI** backend service for a job board application that enables users to create, search, filter, and manage job listings.

---

## ✨ Features

* 🧱 RESTful API for job board operations
* 🔍 Advanced search and filtering
* 🏷️ Tag-based job categorization
* 🛡️ Modification code-based authentication for updates/deletions
* 🧼 HTML sanitization for job descriptions
* 🚫 Rate limiting for security
* ✅ Comprehensive automated testing suite

---

## 🚀 Installation and Setup

### ✅ Prerequisites

* Python 3.9+
* PostgreSQL
* Redis *(optional — used for rate limiting in production)*

### 🛠️ Local Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/eugenemartinez/next-hire-api.git
   cd next-hire-api
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   Create a `.env` file in the root directory with the following content:

   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/nexthire
   REDIS_URL=redis://localhost:6379/0  # Optional
   DEBUG_MODE=True
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

5. **Initialize the database**

   ```bash
   alembic upgrade head
   ```

6. **Start the development server**

   ```bash
   uvicorn main:app --reload
   ```

7. **Access the API documentation**
   Open [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs) in your browser.

---

## 📡 API Endpoints

### 🔧 Job Operations

| Method | Endpoint               | Description                   | Auth Required |
| ------ | ---------------------- | ----------------------------- | ------------- |
| POST   | `/api/jobs`            | Create a new job listing      | No            |
| GET    | `/api/jobs`            | List/search job listings      | No            |
| GET    | `/api/jobs/{job_uuid}` | Get details of a specific job | No            |
| PATCH  | `/api/jobs/{job_uuid}` | Update a job listing          | Yes (Header)  |
| DELETE | `/api/jobs/{job_uuid}` | Delete a job listing          | Yes (Header)  |

### 🛠️ Job Utilities

| Method | Endpoint                      | Description                         |
| ------ | ----------------------------- | ----------------------------------- |
| POST   | `/api/jobs/saved`             | Batch retrieve job details by UUIDs |
| POST   | `/api/jobs/{job_uuid}/verify` | Verify a modification code          |

### 🏷️ Tags

| Method | Endpoint    | Description              |
| ------ | ----------- | ------------------------ |
| GET    | `/api/tags` | List all unique job tags |

---

## 🔐 Authentication

Modification of job listings requires a **modification code**, which is returned upon job creation.
Include this code in the request header:

```
X-Modification-Code: your_code_here
```

---

## 🧪 Running Tests

Run the test suite using:

```bash
pytest
```

---

## 📚 API Documentation

Interactive Swagger docs are available at:
**[http://localhost:8000/api/docs](http://localhost:8000/api/docs)**

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Status](https://img.shields.io/badge/status-active-brightgreen)