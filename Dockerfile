FROM python:3.9-slim-buster

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia requirements e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de archivos
COPY . .

# Configuración crítica para Railway
ENV PORT=8000  # Valor por defecto
EXPOSE $PORT

# Comando de inicio CON FORMATO CORRECTO
CMD gunicorn --bind 0.0.0.0:$PORT app:app  # 👈 Sin corchetes ni comillas
