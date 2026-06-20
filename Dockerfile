FROM python:3.14-slim AS finder-base
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential curl make supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_26.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

FROM finder-base
WORKDIR /app

COPY --from=ghcr.io/techarohq/anubis:latest /ko-app/anubis /ko-app/anubis

COPY . .

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY botPolicy.yaml /data/cfg/botPolicy.yaml

EXPOSE 80

RUN echo "# Set your secrets manually using environment variables" > Makefile.secret
RUN make deps build SHELL=bash

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]