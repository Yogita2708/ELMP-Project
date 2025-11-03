# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
# We install gunicorn first from the file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# --- IMPORTANT ---
# We need to add a command to app.py to initialize the DB
# We will do that in the next step.
# This command creates the 'leave.db' file inside the container
RUN flask init-db

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using gunicorn
# It will listen on all interfaces (0.0.0.0) on port 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "app:app"]