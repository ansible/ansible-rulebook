FROM registry.access.redhat.com/ubi9/python-39

ARG USER_ID=${USER_ID:-1001}
ARG DEVEL_COLLECTION_LIBRARY=0
WORKDIR $HOME

USER 0
RUN pip install -U pip

RUN dnf install -y java-17-openjdk-devel rustc cargo \
    && dnf clean all \
    && rm -rf /var/cache/dnf
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk
RUN pip install -U pip \
    && pip install ansible \
    ansible-runner \
    jmespath \
    asyncio \
    aiohttp \
    aiokafka \
    watchdog \
    azure-servicebus \
    && ansible-galaxy collection install ansible.eda

RUN bash -c "if [ $DEVEL_COLLECTION_LIBRARY -ne 0 ]; then \
    ansible-galaxy collection install git+https://github.com/ansible/event-driven-ansible.git --force; fi"

COPY . $WORKDIR
RUN chown -R $USER_ID ./

USER $USER_ID
RUN pip install .
