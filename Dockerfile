# Use a lightweight Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core script and main entry point
COPY grabIA.py grabia_core.py ./

# Create the downloads directory
RUN mkdir -p /app/downloads

# Define the volume for persistent data (Database and Downloads)
VOLUME ["/app/downloads"]

# Set the entrypoint to run the tool
ENTRYPOINT ["python", "grabIA.py"]

# Default command (expects a file path to be passed during 'docker run')
CMD ["--help"]
