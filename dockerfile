# Imagen base de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema incluyendo FreeTDS para SQL Server
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    tdsodbc \
    freetds-bin \
    freetds-dev \
    locales \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

# Configurar FreeTDS para SQL Server
RUN echo "[FreeTDS]\n\
Description = FreeTDS Driver\n\
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\n\
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so\n\
FileUsage = 1\n\
" > /etc/odbcinst.ini

# Copiar primero solo el archivo requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python desde requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . .

# Asegurarse de que la carpeta Key_Encryptation existe
RUN mkdir -p /app/Key_Encryptation\(NO_BORRAR\)

# Exponer el puerto (5000 es el default de Flask)
EXPOSE 5001

# Comando para ejecutar la app
CMD ["python", "run.py"]