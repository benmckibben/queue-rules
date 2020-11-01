from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Tuple

from django.conf import settings

from data.models import LastCheckLog, UserLock


# For each of these checks, return a tuple of whether the check passed and a dict with
# any additional information on the check.


def most_recent_check() -> Tuple[bool, dict]:
    check = LastCheckLog.get_most_recent_check()
    now = datetime.now(timezone.utc)

    if check is not None:
        check_age = now - check
        result = check_age <= timedelta(
            seconds=settings.MOST_RECENT_CHECK_AGE_THRESHOLD
        )

        return result, {"most_recent_check_age": check_age}
    else:
        return False, {"most_recent_check_age": None}


def stale_locks() -> Tuple[bool, dict]:
    now = datetime.now(timezone.utc)
    num_stale_locks = UserLock.objects.filter(
        created__lte=now - timedelta(seconds=settings.STALE_LOCK_THRESHOLD)
    ).count()

    result = num_stale_locks == 0
    return result, {"num_stale_locks": num_stale_locks}


class ServiceStatus(Enum):
    CRITICAL = 0
    WARNING = 1
    OK = 2


# For each of the above checks, register them as critical checks (indicators that the
# service is down) or warning checks (indicators that the service has degraded).
CRITICAL_CHECKS = (most_recent_check,)
WARNING_CHECKS = (stale_locks,)


def run_checks() -> Tuple[ServiceStatus, dict]:
    """
    Run the checks and return a ServiceStatus indicating the overall service status
    and a dict with any info from the checks.
    """
    all_check_info = {}

    service_critical = False
    for check in CRITICAL_CHECKS:
        check_result, check_info = check()
        service_critical = service_critical | (not check_result)
        all_check_info[check.__name__] = check_info

    service_warning = False
    for check in WARNING_CHECKS:
        check_result, check_info = check()
        service_warning = service_warning | (not check_result)
        all_check_info[check.__name__] = check_info

    service_status = ServiceStatus.OK

    if service_warning:
        service_status = ServiceStatus.WARNING

    if service_critical:
        service_status = ServiceStatus.CRITICAL

    return service_status, all_check_info
