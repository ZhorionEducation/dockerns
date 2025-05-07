# Imagen base de Python (especificando Debian Bullseye)
FROM python:3.11-slim-bullseye

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema, ODBC Driver, PPP y FortiClient VPN
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    curl \
    locales \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    openfortivpn \
    ppp \
    iptables \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

# Buscar la ubicación real del driver y configurarlo correctamente
RUN echo "Buscando la ubicación del driver ODBC..." && \
    find / -name "libmsodbcsql*.so*" 2>/dev/null | tee /tmp/driver_path.txt && \
    DRIVER_PATH=$(cat /tmp/driver_path.txt | head -1) && \
    if [ -z "$DRIVER_PATH" ]; then \
        echo "No se encontró el driver ODBC" && exit 1; \
    else \
        echo "Driver encontrado en: $DRIVER_PATH" && \
        echo "[ODBC Driver 18 for SQL Server]" > /etc/odbcinst.ini && \
        echo "Description=Microsoft ODBC Driver 18 for SQL Server" >> /etc/odbcinst.ini && \
        echo "Driver=$DRIVER_PATH" >> /etc/odbcinst.ini && \
        echo "UsageCount=1" >> /etc/odbcinst.ini; \
    fi && \
    odbcinst -j && \
    cat /etc/odbcinst.ini

# Copiar primero solo el archivo requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python desde requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . .

# Asegurarse de que la carpeta Key_Encryptation existe
RUN mkdir -p /app/Key_Encryptation\(NO_BORRAR\)

# Exponer el puerto
EXPOSE 5001

# Copiar script de inicio y darle permisos de ejecución
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Comando para ejecutar el script de inicio en lugar de run.py directamente
CMD ["/app/start.sh"]