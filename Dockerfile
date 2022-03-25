FROM python:3.8 as builder
ARG EXTRAS
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY poetry.lock poetry.toml pyproject.toml ./
RUN poetry install --extras $EXTRAS
COPY links.json *.py twitfix.ini ./
COPY static/ static/
COPY templates/ templates/

FROM python:3.8-slim-bullseye
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY --from=builder /app/ /app/

ENV PORT=8080

STOPSIGNAL SIGTERM
CMD ["poetry", "run", "python", "-m", "gwsgi"]
