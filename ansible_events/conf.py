import uuid


class _Settings:
    def __init__(self):
        self.identifier = str(uuid.uuid4())


settings = _Settings()
