FROM registry.access.redhat.com/ubi9/python-39

ARG USER_ID=${USER_ID:-1001}
WORKDIR $HOME

USER 0
RUN pip install -U pip \
    && pip install ansible \
    ansible-runner \
    jmespath \
    && ansible-galaxy collection install benthomasson.eda
COPY . $WORKDIR
RUN chown -R $USER_ID ./

USER $USER_ID
RUN pip install .
