# Demonstration-only image. Adds the trust tooling the local HTTPS mirror needs
# and nothing else: the application, its dependencies, and its configuration all
# come from the shipped image unchanged.
ARG BASE_IMAGE=bank-tariff-monitoring-agent-api
FROM ${BASE_IMAGE}

# certutil installs the demonstration root into the NSS database Chromium reads.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libnss3-tools \
    && rm -rf /var/lib/apt/lists/*

COPY demo/bin/demo-entrypoint.sh /usr/local/bin/demo-entrypoint.sh
RUN chmod +x /usr/local/bin/demo-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/demo-entrypoint.sh"]
