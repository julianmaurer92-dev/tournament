#!/bin/bash
#
# Jugendfussballturnier - Installation Script
# Fuer Ubuntu/Debian VPS (z.B. Strato)
#
# Verwendung:
#   curl -sSL https://raw.githubusercontent.com/julianmaurer92-dev/tournament/main/install.sh | bash
#
# Oder manuell:
#   chmod +x install.sh && ./install.sh
#

set -e

# Farben fuer Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Jugendfussballturnier - Installation ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Root-Check
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Bitte als root ausfuehren: sudo ./install.sh${NC}"
    exit 1
fi

# Variablen
APP_DIR="/opt/tournament"
APP_USER="tournament"
DOMAIN=""

# Domain abfragen
echo -e "${YELLOW}Gib deine Domain ein (z.B. turnier.example.de) oder leer lassen fuer IP-Zugriff:${NC}"
read -r DOMAIN

# System aktualisieren
echo -e "${GREEN}[1/7] System aktualisieren...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# Docker installieren (falls nicht vorhanden)
echo -e "${GREEN}[2/7] Docker installieren...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "Docker bereits installiert"
fi

# Docker Compose installieren (falls nicht vorhanden)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    apt-get install -y -qq docker-compose-plugin
fi

# App-User erstellen
echo -e "${GREEN}[3/7] App-User erstellen...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
fi

# App-Verzeichnis erstellen
echo -e "${GREEN}[4/7] App herunterladen...${NC}"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Repository klonen oder aktualisieren
if [ -d "$APP_DIR/.git" ]; then
    git pull origin main
else
    git clone https://github.com/julianmaurer92-dev/tournament.git .
fi

# Sichere Passwoerter generieren
echo -e "${GREEN}[5/7] Konfiguration erstellen...${NC}"
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '=/+' | head -c 16)
DB_PASSWORD=$(openssl rand -hex 16)

# docker-compose.override.yml mit sicheren Werten erstellen
cat > docker-compose.override.yml << EOF
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  web:
    environment:
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      DATABASE_URL: postgresql://tournament:${DB_PASSWORD}@db:5432/tournament
    ports:
      - "80:5000"
EOF

# Berechtigungen setzen
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Container starten
echo -e "${GREEN}[6/7] Container starten...${NC}"
docker compose down 2>/dev/null || true
docker compose up -d --build

# Warten auf Start
echo -e "${YELLOW}Warte auf Container-Start...${NC}"
sleep 10

# Status pruefen
echo -e "${GREEN}[7/7] Installation abgeschlossen!${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation erfolgreich!            ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Server-IP ermitteln
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo -e "Zugangsdaten:"
echo -e "  ${YELLOW}URL:${NC}            http://${DOMAIN:-$SERVER_IP}/"
echo -e "  ${YELLOW}Admin-Panel:${NC}    http://${DOMAIN:-$SERVER_IP}/admin/login"
echo -e "  ${YELLOW}Admin-Passwort:${NC} ${RED}${ADMIN_PASSWORD}${NC}"
echo ""
echo -e "${YELLOW}WICHTIG: Notiere dir das Admin-Passwort!${NC}"
echo ""

# Credentials in Datei speichern
cat > "$APP_DIR/.credentials" << EOF
# Turnier-App Zugangsdaten
# Erstellt: $(date)

URL: http://${DOMAIN:-$SERVER_IP}/
Admin-Panel: http://${DOMAIN:-$SERVER_IP}/admin/login
Admin-Passwort: ${ADMIN_PASSWORD}
Secret-Key: ${SECRET_KEY}
DB-Passwort: ${DB_PASSWORD}
EOF
chmod 600 "$APP_DIR/.credentials"
echo -e "Zugangsdaten gespeichert in: ${YELLOW}$APP_DIR/.credentials${NC}"
echo ""

# Optional: Nginx + SSL
if [ -n "$DOMAIN" ]; then
    echo -e "${YELLOW}Moechtest du HTTPS mit Let's Encrypt einrichten? (j/n)${NC}"
    read -r SETUP_SSL
    if [ "$SETUP_SSL" = "j" ] || [ "$SETUP_SSL" = "J" ]; then
        echo -e "${GREEN}Nginx und Certbot installieren...${NC}"
        apt-get install -y -qq nginx certbot python3-certbot-nginx

        # Nginx Config
        cat > /etc/nginx/sites-available/tournament << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF
        ln -sf /etc/nginx/sites-available/tournament /etc/nginx/sites-enabled/
        rm -f /etc/nginx/sites-enabled/default

        # Port auf 5000 aendern (Nginx uebernimmt Port 80)
        sed -i 's/"80:5000"/"127.0.0.1:5000:5000"/' "$APP_DIR/docker-compose.override.yml"
        docker compose up -d

        nginx -t && systemctl reload nginx

        # SSL Zertifikat
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect

        echo -e "${GREEN}HTTPS eingerichtet!${NC}"
        echo -e "  ${YELLOW}URL:${NC} https://${DOMAIN}/"
    fi
fi

echo ""
echo -e "${GREEN}Fertig! Die App laeuft jetzt.${NC}"
echo ""
echo -e "Nuetzliche Befehle:"
echo -e "  ${YELLOW}Logs anzeigen:${NC}     cd $APP_DIR && docker compose logs -f"
echo -e "  ${YELLOW}Neustart:${NC}          cd $APP_DIR && docker compose restart"
echo -e "  ${YELLOW}Update:${NC}            cd $APP_DIR && git pull && docker compose up -d --build"
echo -e "  ${YELLOW}Status:${NC}            cd $APP_DIR && docker compose ps"
