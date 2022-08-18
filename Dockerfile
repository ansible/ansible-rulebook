FROM registry.access.redhat.com/ubi8/python-39

ARG USER_ID=${USER_ID:-1001}
WORKDIR $HOME

USER 0
RUN pip install -U pip \
    && pip install ansible \
    ansible-runner \
    jmespath \
    asyncio \
    aiohttp \
    aiokafka \
    watchdog \
    azure-servicebus \
    && ansible-galaxy collection install benthomasson.eda

COPY . $WORKDIR
RUN chown -R $USER_ID ./

USER $USER_ID
RUN pip install .
