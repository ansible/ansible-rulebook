FROM registry.access.redhat.com/ubi8/python-39

ARG USER_ID=${USER_ID:-1001}
ARG DEVEL_COLLECTION_LIBRARY=0
ARG DEVEL_COLLECTION_REPO=git+https://github.com/ansible/event-driven-ansible.git
WORKDIR $HOME

USER 0
RUN dnf install -y java-17-openjdk-devel
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
    ansible-galaxy collection install ${DEVEL_COLLECTION_REPO} --force; fi"

COPY . $WORKDIR
RUN chown -R $USER_ID ./

USER $USER_ID
RUN pip install .
