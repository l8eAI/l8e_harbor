FROM curlimages/curl:latest as base
USER root
RUN apk add --no-cache jq openssl bash

FROM base as admin-init
WORKDIR /app
COPY admin-init.sh /app/admin-init.sh
RUN chmod +x /app/admin-init.sh
ENTRYPOINT ["/app/admin-init.sh"]