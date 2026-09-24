#!/bin/bash
# =============================================================================
# ec2_bootstrap.sh — One-shot bootstrap for AWS EC2 t2.micro (Amazon Linux 2023)
#
# Usage (as EC2 User Data, or run manually after SSH):
#   bash ec2_bootstrap.sh
#
# What it does:
#   1. Installs Python 3.12, git, nginx
#   2. Clones the repo (or pulls if already present)
#   3. Creates a Python venv and installs requirements
#   4. Copies your .env file into place
#   5. Runs migrations + collectstatic
#   6. Installs and enables the systemd service
#   7. Configures nginx as a reverse proxy on port 80
#
# Pre-requisites:
#   - Set all env vars in /home/ec2-user/carmechanic/.env before running
#     (or set them after cloning the repo)
#   - The EC2 security group must allow inbound TCP 80 and 443
# =============================================================================

set -euo pipefail

REPO_URL="https://github.com/YOUR_GITHUB_USER/ai-car-mechanic.git"
APP_DIR="/home/ec2-user/ai-car-mechanic"
BACKEND_DIR="$APP_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
SERVICE_NAME="carmechanic"
USER="ec2-user"

echo "==> [1/7] Installing system dependencies..."
dnf update -y
dnf install -y python3.12 python3.12-pip git nginx

echo "==> [2/7] Cloning / updating repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> [3/7] Setting up Python virtual environment..."
cd "$BACKEND_DIR"
python3.12 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo "==> [4/7] Running migrations and collectstatic..."
# .env must exist at this point with DEBUG=False, SECRET_KEY, etc.
"$VENV_DIR/bin/python" manage.py migrate --noinput
"$VENV_DIR/bin/python" manage.py collectstatic --noinput

echo "==> [5/7] Installing systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=AI Car Mechanic — Django + Gunicorn
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn carmechanic.wsgi \
    --config $BACKEND_DIR/gunicorn.conf.py
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo "==> [6/7] Configuring nginx reverse proxy..."
cat > /etc/nginx/conf.d/$SERVICE_NAME.conf << 'EOF'
server {
    listen 80;
    server_name _;   # replace with your domain if using one

    # Django API + admin
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host             $host;
        proxy_set_header   X-Real-IP        $remote_addr;
        proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 130s;   # > gunicorn timeout
        client_max_body_size 30M;  # allow up to 30 MB uploads (video limit 25 MB)
    }

    # Serve Django media uploads directly via nginx (faster than gunicorn)
    location /media/ {
        alias /home/ec2-user/ai-car-mechanic/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

nginx -t && systemctl enable nginx && systemctl restart nginx

echo ""
echo "================================================================"
echo " Bootstrap complete!"
echo " Gunicorn: $(systemctl is-active $SERVICE_NAME)"
echo " Nginx:    $(systemctl is-active nginx)"
echo ""
echo " IMPORTANT — SQLite storage note:"
echo "   The database is stored at $BACKEND_DIR/db.sqlite3"
echo "   This is on the EC2 instance's EBS root volume."
echo "   It WILL PERSIST across reboots (EBS is not ephemeral)."
echo "   However, it WILL BE LOST if the instance is TERMINATED."
echo "   For production beyond MVP: migrate to RDS PostgreSQL."
echo ""
echo " Next steps:"
echo "   1. Set your Vercel frontend URL in FRONTEND_ORIGIN env var"
echo "   2. systemctl restart $SERVICE_NAME"
echo "================================================================"
