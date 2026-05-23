# 🚌 BusGo – Deployment Guide
## VS Code (Local Dev) + EC2 via PuTTY

---

## 📁 Project Structure
```
bus_booking/
├── app.py                  ← Flask app (all routes + models)
├── requirements.txt
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── book.html
    ├── my_bookings.html
    ├── admin_dashboard.html
    ├── admin_buses.html
    └── admin_users.html
```

---

## 💻 STEP 1 — Run Locally in VS Code

```bash
# 1. Open the bus_booking folder in VS Code
# 2. Open a terminal (Ctrl + `)

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open browser → http://localhost:5000

**Default Admin Login:**
- Email: `admin@busbooking.com`
- Password: `Admin@123`

---

## ☁️ STEP 2 — Deploy on AWS EC2 via PuTTY

### 2a. Connect to EC2 using PuTTY
1. Open PuTTY → enter your EC2 **Public IP**
2. Go to Connection → SSH → Auth → browse for your `.ppk` key file
3. Click **Open** → login as `ubuntu`

### 2b. Install Python & dependencies on EC2
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx -y
```

### 2c. Upload project files (use WinSCP or scp)
```bash
# From your local machine terminal or Git Bash:
scp -i your-key.pem -r bus_booking/ ubuntu@YOUR_EC2_IP:~/
```
Or use **WinSCP** (drag and drop from local to EC2).

### 2d. Set up the app on EC2 (PuTTY terminal)
```bash
cd ~/bus_booking
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Test it runs:
```bash
python3 app.py
# Ctrl+C to stop
```

### 2e. Run with Gunicorn (production server)
```bash
# Still inside the venv
gunicorn --bind 0.0.0.0:5000 app:app --daemon
```

### 2f. Configure Nginx as Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/busgo
```

Paste this config:
```nginx
server {
    listen 80;
    server_name YOUR_EC2_PUBLIC_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/busgo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2g. Open port 80 in EC2 Security Group
In AWS Console → EC2 → Security Groups → Inbound Rules:
- Add rule: **HTTP (port 80)**, Source: **0.0.0.0/0**

Now open: `http://YOUR_EC2_PUBLIC_IP` in your browser ✅

---

## 🔒 Security Group Rules Summary

| Type  | Port | Source    | Purpose              |
|-------|------|-----------|----------------------|
| SSH   | 22   | Your IP   | PuTTY access         |
| HTTP  | 80   | 0.0.0.0/0 | Web app access       |
| HTTPS | 443  | 0.0.0.0/0 | SSL (after cert)     |

---

## 🗄️ Using MySQL/PostgreSQL (RDS) instead of SQLite

In `app.py`, change the DATABASE_URL:
```python
# For MySQL (RDS):
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'mysql+pymysql://username:password@RDS_ENDPOINT:3306/bus_db'

# Install driver:
# pip install PyMySQL
```

---

## ✅ Default Credentials
| Role  | Email                    | Password  |
|-------|--------------------------|-----------|
| Admin | admin@busbooking.com     | Admin@123 |

Change the admin password after first login via the DB or by updating seed() in app.py.
