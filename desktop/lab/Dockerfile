FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=UTC
RUN apt-get update && apt-get install -y --no-install-recommends bash coreutils findutils grep curl wget tar gzip unzip zip dpkg procps python3 ca-certificates nano && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 1100 --create-home --shell /bin/bash learner
COPY lab.py bridge.py /opt/shellground/
RUN python3 /opt/shellground/lab.py fixtures
USER 1100:1100
WORKDIR /home/learner
CMD ["python3", "-u", "/opt/shellground/lab.py", "serve"]
