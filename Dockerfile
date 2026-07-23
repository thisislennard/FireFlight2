FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system fireflight2 \
    && useradd --system --gid fireflight2 --home-dir /app --shell /usr/sbin/nologin fireflight2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh
# Verzeichnis für Nutzer-Uploads (Profilbilder, app/core/utilities/uploads.py) muss VOR dem chown
# existieren -- Docker übernimmt beim ersten Mounten eines named volumes Inhalt+Rechte aus dem
# Image-Verzeichnis, ist es hier nicht mit korrekten Rechten angelegt, kann der non-root-Prozess
# später nicht hineinschreiben (docker-compose.yml: fireflight2-uploads-data).
RUN mkdir -p /app/instance/uploads/profile_images \
    && chmod +x /entrypoint.sh \
    && chown -R fireflight2:fireflight2 /app

USER fireflight2

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "run:app"]
