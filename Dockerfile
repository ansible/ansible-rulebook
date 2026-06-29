FROM quay.io/centos/centos:stream9-minimal AS builder

# FIRST PHASE: build wheels, fetch ansible.eda collection

USER root

ARG SETUPTOOLS_SCM_PRETEND_VERSION
# This parameter can be set to any location for the collection, including
# git repositories:
# https://docs.ansible.com/projects/ansible/latest/collections_guide/collections_installing.html
ARG DEVEL_COLLECTION_REPO=ansible.eda
ARG ANSIBLE_CORE_VER=${ANSIBLE_CORE_VER:-2.16.14}

ENV PIP_BUILD_OPTS="--use-pep517 --disable-pip-version-check --wheel-dir /output/wheels"

# Install all the needed build dependencies
RUN microdnf update --setopt=install_weak_deps=0 -y && \
    microdnf install --setopt=install_weak_deps=0 -y \
      gcc \
      git-core \
      java-17-openjdk-devel \
      krb5-devel \
      libyaml \
      postgresql-devel \
      python3.12 \
      python3.12-devel \
      python3.12-pip

# Use /output as place where to save all the build artifacts, so they are
# copied to the final phase at once
RUN mkdir -p /output

# Same requirements as in ansible.eda requirements.txt, with:
# - psycopg[binary,pool] replaced by psycopg & psycopg-c
# - systemd-python removed
RUN cat > /output/requirements-collection.txt <<EOF
pyyaml>=6.0.1
aiobotocore
aiohttp
aiokafka[gssapi]
fastavro
azure-servicebus
dpath
kafka-python-ng
psycopg
psycopg-c
watchdog>=5.0.0
xxhash
EOF

# Build the wheels for the collection
# (some may be already built by the previous step)
RUN python3.12 -m pip wheel ${PIP_BUILD_OPTS} -r /output/requirements-collection.txt

# Build the wheels for ansible-core
# (some may be already built by the previous steps)
RUN python3.12 -m pip wheel ${PIP_BUILD_OPTS} "ansible-core==${ANSIBLE_CORE_VER}"

# Import the current sources to be built
COPY . /tmp/ansible-rulebook

# Extract the requirements of ansible-rulebook, replacing psycopg[binary] with psycopg & psycopg-c
RUN python3.12 - > /output/requirements-rulebook.txt <<EOF
import configparser
cfg = configparser.ConfigParser()
cfg.read("/tmp/ansible-rulebook/setup.cfg")
reqs = [r for r in cfg.get("options", "install_requires").splitlines() if r]
for r in reqs:
    if "psycopg[binary]" in r:
        print(r.replace("psycopg[binary]", "psycopg"))
        print(r.replace("psycopg[binary]", "psycopg-c"))
    else:
        print(r)
EOF

# Build the wheels for ansible-rulebook itself
RUN python3.12 -m pip wheel ${PIP_BUILD_OPTS} -r /output/requirements-rulebook.txt

# Build the wheel of ansible-rulebook itself
RUN cd /tmp/ansible-rulebook && \
    python3.12 -m pip wheel --no-deps ${PIP_BUILD_OPTS} .

# Fetch the wanted ansible.eda collection, "installing" it
# to the local output directory; for this we need to install ansible-core
RUN python3.12 -m pip install --no-cache-dir --no-index --find-links /output/wheels ansible-core
RUN ansible-galaxy collection install -p /output/collections "${DEVEL_COLLECTION_REPO}"

# LAST PHASE: assemble the final image

FROM quay.io/centos/centos:stream9-minimal

ARG USER_ID=1001

# Install the runtime dependencies needed
RUN microdnf update --setopt=install_weak_deps=0 -y && \
    microdnf install --setopt=install_weak_deps=0 -y \
      java-17-openjdk-headless \
      krb5-libs \
      libpq \
      libyaml \
      python3.12 \
      python3.12-pip && \
    microdnf clean all && \
    rm -rf /var/cache/yum

# support random uid number and gid 0 for openshift
RUN useradd --uid "$USER_ID" --gid 0 --create-home --key HOME_MODE=0770 --home-dir /app appuser && \
    chmod -R g+w /app

# Copy all the artifacts from the build phase
COPY --from=builder /output /tmp/output

# - install all the wheels (ansible-core, ansible-rulebook, and all the dependencies)
# - copy the installed ansible.eda collection in the right place
# - set a "pip3" compatibility symlink
# - cleanup bits & caches
RUN python3.12 -m pip install --no-cache-dir --no-index --find-links /tmp/output/wheels -r /tmp/output/requirements-rulebook.txt && \
    python3.12 -m pip install --no-cache-dir --no-index --find-links /tmp/output/wheels -r /tmp/output/requirements-collection.txt && \
    python3.12 -m pip install --no-cache-dir --no-index --find-links /tmp/output/wheels ansible-core && \
    python3.12 -m pip install --no-cache-dir --no-index --find-links /tmp/output/wheels --no-deps ansible_rulebook && \
    mkdir -p /usr/share/ansible/ && \
    cp -r /tmp/output/collections /usr/share/ansible/collections && \
    ln -s ./pip3.12 /usr/bin/pip3 && \
    rm -rf /tmp/* /root/.cache

USER $USER_ID
WORKDIR /app
