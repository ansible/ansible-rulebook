FROM quay.io/centos/centos:stream9-development

ARG USER_ID=${USER_ID:-1001}
ARG APP_DIR=${APP_DIR:-/app}
ARG DEVEL_COLLECTION_LIBRARY=0
ARG DEVEL_COLLECTION_REPO=git+https://github.com/ansible/event-driven-ansible.git

USER 0
RUN useradd -u $USER_ID -d $APP_DIR appuser
WORKDIR $APP_DIR
COPY . $WORKDIR
RUN chown -R $USER_ID $APP_DIR
RUN dnf install -y java-17-openjdk-devel python3-pip gcc python-devel

USER $USER_ID
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk
ENV PATH="${PATH}:$APP_DIR/.local/bin"
RUN pip install -U pip \
    && pip install ansible-core \
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

RUN pip install .

RUN chmod -R 0775 $APP_DIR
