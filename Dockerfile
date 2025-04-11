FROM quay.io/centos/centos:stream9

ARG USER_ID=${USER_ID:-1001}
ARG APP_DIR=${APP_DIR:-/app}
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ARG DEVEL_COLLECTION_LIBRARY=0
ARG DEVEL_COLLECTION_REPO=git+https://github.com/ansible/event-driven-ansible.git

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk
ENV PATH="$APP_DIR/.local/bin:$PATH"
ENV PYTHONPATH="$APP_DIR/.local/lib/python3.9/site-packages:$PYTHONPATH"
ENV HOME=$APP_DIR

USER 0

# support random uid number and gid 0 for openshift
RUN for dir in \
    $APP_DIR \
    $APP_DIR/.local \
    $APP_DIR/.local/bin \
    $APP_DIR/.local/lib \
    $APP_DIR/.local/lib/python3.9/site-packages \
    $APP_DIR/.ansible; \
    do mkdir -p $dir ; chown -R "${USER_ID}:0" $dir ; chmod 0775 $dir ; done \
    && useradd --uid "$USER_ID" --gid 0 --home-dir "$APP_DIR" appuser

RUN dnf install -y java-17-openjdk-devel python3-pip postgresql-devel gcc python3-devel git krb5-libs krb5-devel

USER $USER_ID
WORKDIR $APP_DIR
COPY --chown=${USER_ID}:0 . $WORKDIR

RUN pip install -U pip \
    && pip install ansible-core \
    ansible-runner \
    jmespath \
    aiohttp \
    aiokafka[gssapi] \
    watchdog \
    azure-servicebus \
    aiobotocore \
    && ansible-galaxy collection install ansible.eda

RUN bash -c "if [ $DEVEL_COLLECTION_LIBRARY -ne 0 ]; then \
    ansible-galaxy collection install ${DEVEL_COLLECTION_REPO} --force; fi"

RUN pip install .[production]
