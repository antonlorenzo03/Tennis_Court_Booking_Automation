FROM selenium/standalone-chrome:114.0

USER root

# Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER=true

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run your script
CMD ["python", "tennis_consecutive_slots_booking.py"]
