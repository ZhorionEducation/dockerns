#!/bin/bash
set -e

# Crear un archivo de configuración para la VPN
cat > /tmp/vpnconfig.conf << EOF
host = 200.122.221.2
port = 10443
username = amjimenez
password = ktm1290*
trusted-cert = 374134afe7279d6f6f5d848a5ee61511bd5abd4e2275f15abb5475691f0ea3da
EOF

# Configurar e iniciar la conexión VPN usando el archivo de configuración
echo "Iniciando conexión VPN con archivo de configuración..."
openfortivpn -c /tmp/vpnconfig.conf &

# Esperar a que se establezca la conexión
sleep 10

# Instalar el comando 'ip' para verificar las interfaces
which ip >/dev/null || (echo "Instalando iproute2..." && apt-get update -y && apt-get install -y iproute2)

# Verificar si la VPN está funcionando
if ip addr | grep -q ppp0; then
    echo "Conexión VPN establecida correctamente."
else
    echo "ADVERTENCIA: La conexión VPN podría no haberse establecido correctamente."
    
    # Intentar ver los logs para diagnosticar
    echo "Últimos mensajes del sistema:"
    dmesg | tail -20
fi

# Iniciar la aplicación
echo "Iniciando la aplicación..."
exec python run.py