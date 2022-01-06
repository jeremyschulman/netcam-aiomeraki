#  Copyright 2021 Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TypeVar
from http import HTTPStatus

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from meraki.aio import AsyncDashboardAPI as _AsyncDashboardAPI, AsyncAPIError
from tenacity import (
    retry,
    stop_after_attempt,
    RetryCallState,
    wait_exponential,
)

from netcad.logger import get_logger

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["AsyncDashboardAPI", "AsyncAPIError", "AsyncAPIErrorLike"]


AsyncAPIErrorLike = TypeVar("AsyncAPIErrorLike", AsyncAPIError, BaseException)

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


def retry_on_429(retry_state: RetryCallState):
    """tenacity handler for checking the return status of 429"""

    oc = retry_state.outcome
    if not oc.failed:
        return False

    # if the exception is a 429, then we are going to backoff
    # and try again.

    rt_exc: AsyncAPIErrorLike = retry_state.outcome.exception()
    if not hasattr(rt_exc, "status"):
        return False

    if rt_exc.status == HTTPStatus.TOO_MANY_REQUESTS:
        return True

    # otherwise, we've tried hard enough and we should stop trying.
    # this will result in a RetryError in the calling context.
    return False


def my_before_sleep(retry_state: RetryCallState):
    sleep_sec = retry_state.next_action.sleep
    get_logger().debug(
        f"Still working on Meraki request. retry attempt {retry_state.attempt_number}, sleep: {sleep_sec}"
    )


api_request_retry = retry(
    retry=retry_on_429,
    before_sleep=my_before_sleep,
    wait=wait_exponential(min=10, max=120),
    stop=stop_after_attempt(5),
)


class AsyncDashboardAPI(_AsyncDashboardAPI):
    def __init__(self, *vargs, **kwargs):
        super().__init__(*vargs, **kwargs)
        self._session.request = api_request_retry(self._session.request)
