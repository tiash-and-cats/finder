# Stage 1: base with system deps
FROM python:3.14-slim AS finder-base
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential curl make \
    && curl -fsSL https://deb.nodesource.com/setup_26.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: final runtime
FROM finder-base
WORKDIR /app

COPY . .

EXPOSE 80

RUN echo "# Set your secrets manually using environment variables" > Makefile.secret
RUN make deps build SHELL=bash

CMD make run SHELL=bash