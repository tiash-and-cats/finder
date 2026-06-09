FROM python:3.14-slim

# Copy to working dir
COPY . /app

# Change to working directory
WORKDIR /app

# Blank out Makefile.secret
RUN echo "# Set your secrets manually via environment variables" > Makefile.secret

# Install Node.js (for Find4U frontend)
RUN apt-get update && apt-get install -y curl make \
    && curl -fsSL https://deb.nodesource.com/setup_26.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies and create venv
RUN make deps SHELL=bash

# Expose port 80
EXPOSE 80

# Run Makefile (launches unified server)
CMD ["make", "SHELL=bash"]