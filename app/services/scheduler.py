import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.services.mailer_service import execute_job_by_id  # schlanker Orchestrations-Call
from app.core import models

logger = logging.getLogger(__name__)
_scheduler: Optional[BackgroundScheduler] = None


def _get_scheduler() -> BackgroundScheduler:
    """
    Retrieves the global instance of the background scheduler.

    This function ensures that a singleton instance of `BackgroundScheduler`
    is created and initialized with a job event listener. The listener is
    added to capture job execution and error events.

    :raises NoneType: Does not explicitly raise an exception.
    :returns: The global `BackgroundScheduler` instance.
    :rtype: BackgroundScheduler
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    return _scheduler


def _on_job_event(event) -> None:
    """
    Handles job events triggered during the scheduler's operation. Logs the result
    of a job, whether it ended successfully or failed.

    :param event: Event object containing information about the job that triggered
        the event.
    :type event: Any
    :return: None
    """
    if event.exception:
        logger.error(f"[Scheduler] Job {event.job_id} fehlgeschlagen.")
    else:
        logger.info(f"[Scheduler] Job {event.job_id} erfolgreich beendet.")


def start_scheduler() -> None:
    """
    Starts the scheduler if it is not already running.

    This function retrieves the scheduler instance and checks if it is currently
    running. If the scheduler is not active, it will be started, and a log entry
    will be created to indicate the scheduler has started.

    :raises RuntimeError: If the scheduler could not be retrieved or initialized.

    :return: None
    """
    sched = _get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("[Scheduler] gestartet")


def stop_scheduler() -> None:
    """
    Stops the currently running scheduler if it is active.

    This function retrieves the scheduler instance and checks if it is currently
    running. If the scheduler is running, it shuts it down without waiting for
    currently executing jobs to finish. A log entry is then recorded indicating
    that the scheduler has been stopped.

    :return: None
    """
    sched = _get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("[Scheduler] gestoppt")


def _job_id(job_id: int) -> str:
    """
    Generates a formatted string representing a job identifier.

    This function constructs a string by prefixing the provided `job_id` with
    the string 'job_'.

    :param job_id: The unique identifier for a job
    :type job_id: int
    :return: A formatted job identifier string prefixed with 'job_'
    :rtype: str
    """
    return f"job_{job_id}"


def unschedule(job_id: int) -> None:
    """
    Unschedules a job identified by its job_id from the scheduler. If the job exists
    in the scheduler, it will be removed and appropriate log information is recorded.

    :param job_id: The unique identifier of the job to be unscheduled.
    :type job_id: int
    :return: None
    """
    sched = _get_scheduler()
    job = sched.get_job(_job_id(job_id))
    if job:
        sched.remove_job(job.id)
        logger.info(f"[Scheduler] Job {job_id} entfernt")


def register_job(job: models.MailerJob) -> None:
    """
    Registers a job in the scheduler. Depending on the job configuration, it will either schedule
    a cron job or a one-time job. If the job's configuration does not include either a cron definition
    or a specific execution time (`once_at`), the job will not be scheduled. Existing definitions
    for the provided job ID will first be unscheduled before re-registering.

    :param job: The job instance to be scheduled. It must include a unique identifier (`id`)
                and either a cron string (`cron`) or single execution time (`once_at`) to
                determine the job's scheduling configuration.
    :type job: models.MailerJob
    :return: None
    """
    sched = _get_scheduler()
    # Zuerst ggf. vorhandene Definition entfernen
    unschedule(job.id)

    if job.cron:
        parts = job.cron.split()
        if len(parts) != 5:
            logger.error(f"[Scheduler] Ungültiger Cron-String für Job {job.id}: '{job.cron}'")
            return

        minute, hour, day, month, weekday = parts
        sched.add_job(
            execute_job_by_id,                 # direkte Service-Funktion, kein Wrapper hier
            trigger="cron",
            id=_job_id(job.id),
            replace_existing=True,
            args=[job.id],
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=weekday,
        )
        logger.info(f"[Scheduler] Job {job.id} als Cron '{job.cron}' registriert.")
        return

    if job.once_at:
        run_date = job.once_at
        # Nur in der Zukunft planen
        if run_date <= datetime.now(run_date.tzinfo or None):
            logger.info(f"[Scheduler] Once-Job {job.id} liegt in der Vergangenheit – nicht geplant.")
            return

        sched.add_job(
            execute_job_by_id,
            trigger="date",
            id=_job_id(job.id),
            replace_existing=True,
            run_date=run_date,
            args=[job.id],
        )
        logger.info(f"[Scheduler] Once-Job {job.id} für {run_date} geplant.")
        return

    logger.info(f"[Scheduler] Job {job.id} hat weder cron noch once_at – nicht geplant.")


def resync_all_jobs(jobs: list[models.MailerJob]) -> None:
    """
    Syncs the provided list of mailer jobs to ensure they are registered in the system.

    This function takes a list of `MailerJob` objects and registers each
    job to ensure they are properly synced with the system.

    :param jobs: A list of `MailerJob` objects to be resynced.
    :type jobs: list[models.MailerJob]
    :return: None
    """
    for j in jobs:
        register_job(j)
