# Use a lightweight Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy requirements and install
# We use requirements.txt here for faster layer caching in Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project scripts
# Ensure grabia_core.py is present so the CLI/TUI can import it
COPY . .

# Create the downloads directory
RUN mkdir -p /app/downloads

# Define the volume for persistent data
# This saves the SQLite DB and the downloaded files
VOLUME ["/app/downloads"]

# Set the entrypoint to the TUI (Rich Dashboard)
# Docker users usually run headless, so the TUI is better than the GUI
ENTRYPOINT ["python", "grabIA.py"]

CMD ["--help"]
