#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import uuid


class _Settings:
    def __init__(self):
        self.identifier = str(uuid.uuid4())
        self.gc_after = 1000
        self.default_execution_strategy = "sequential"
        self.max_feedback_timeout = 5
        self.print_events = False
        self.websocket_url = None
        self.websocket_ssl_verify = "yes"
        self.websocket_token_url = None
        self.websocket_access_token = None
        self.websocket_refresh_token = None
        self.skip_audit_events = False


settings = _Settings()
