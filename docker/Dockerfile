# --- Builder stage

# Use Python 3.14 base image
FROM python:3.14-slim AS builder

# Copy to working directory
COPY . /app

# --- Runtime stage
FROM python:3.14-slim

# Change to working directory
WORKDIR /app

# Copy from builder
COPY --from=builder /app /app

# Install Node.js (for Find4U frontend)
RUN apt-get update && apt-get install -y curl make \
    && curl -fsSL https://deb.nodesource.com/setup_26.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies and create venv
RUN bash -c "make deps SHELL=bash"

# Expose port 80
EXPOSE 80

# Run Makefile (launches unified server)
CMD ["bash", "-c", "ls && ls env && make SHELL=bash"]