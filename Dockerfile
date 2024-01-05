ARG USER_ID=${USER_ID:-1001}
ARG APP_DIR=${APP_DIR:-/app}

FROM quay.io/centos/centos:stream9 as build

ARG USER_ID
ARG APP_DIR
ARG DEVEL_COLLECTION_LIBRARY=0
ARG DEVEL_COLLECTION_REPO=git+https://github.com/ansible/event-driven-ansible.git

RUN dnf install -y java-17-openjdk-devel java-17-openjdk-jmods binutils python3-pip
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk

ENV PATH="$APP_DIR/venv/bin:${PATH}"

RUN python3 -m venv $APP_DIR/venv \
    && pip install -U pip \
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

WORKDIR $APP_DIR
COPY . $WORKDIR

RUN pip install .

RUN $JAVA_HOME/bin/jdeps \
    --ignore-missing-deps \
    --print-module-deps \
    --multi-release 17 \
    --recursive \
    $(find $APP_DIR -path '*/drools/jars/*' -name 'drools*.jar') > $APP_DIR/drools_jar_modules \
    && $JAVA_HOME/bin/jlink \
    --add-modules $(cat $APP_DIR/drools_jar_modules) \
    --strip-debug \
    --no-man-pages \
    --no-header-files \
    --compress=2 \
    --output $APP_DIR/custom_jre

FROM quay.io/centos/centos:stream9-minimal as dist

ARG USER_ID
ARG APP_DIR

ENV PATH="$APP_DIR/venv/bin:${PATH}"
ENV JAVA_HOME=/jre

COPY --from=build $APP_DIR/custom_jre $JAVA_HOME
COPY --from=build $APP_DIR/venv $APP_DIR/venv

RUN microdnf install -y shadow-utils \
    && useradd -u $USER_ID -d $APP_DIR appuser \
    && chown -R $USER_ID $APP_DIR \
    && chmod -R 0775 $APP_DIR \
    && microdnf clean all

WORKDIR $APP_DIR
USER $USER_ID
