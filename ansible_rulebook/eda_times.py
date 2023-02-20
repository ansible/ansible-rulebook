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

import time
from datetime import datetime


def get_eda_times():
    epoch = time.time()
    return dict(
        ansible_eda_date_time_local=_get_ansible_eda_date_time_local(epoch),
        ansible_eda_date_time_utc=_get_ansible_eda_date_time_utc(epoch),
    )


def _get_ansible_eda_date_time_local(epoch):
    dt = datetime.fromtimestamp(epoch)
    return dict(
        date=dt.strftime("%Y-%m-%d"),
        day=dt.day,
        epoch=int(epoch),
        hour=dt.hour,
        iso8601=dt.astimezone().isoformat(),
        iso8601_micro=f"{dt.isoformat()}",
        minute=dt.minute,
        month=dt.month,
        second=dt.second,
        time=dt.strftime("%H:%M:%S"),
        tz=dt.astimezone().tzname(),
        weekday=dt.strftime("%A"),
        weekday_number=dt.weekday(),
        weeknumber=dt.isocalendar()[1],
        year=dt.year,
    )


def _get_ansible_eda_date_time_utc(epoch):
    dt = datetime.utcfromtimestamp(epoch)
    return dict(
        date=dt.strftime("%Y-%m-%d"),
        day=dt.day,
        epoch=int(epoch),
        hour=dt.hour,
        iso8601=dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        iso8601_micro=f"{dt.isoformat()}Z",
        minute=dt.minute,
        month=dt.month,
        second=dt.second,
        time=dt.strftime("%H:%M:%S"),
        tz="UTC",
        weekday=dt.strftime("%A"),
        weekday_number=dt.weekday(),
        weeknumber=dt.isocalendar()[1],
        year=dt.year,
    )
