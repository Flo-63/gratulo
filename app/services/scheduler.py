"""
===============================================================================
Project   : gratulo
Module    : app/services/scheduler.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides functionality for scheduling and executing jobs.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.services.mailer_service import execute_job_by_id
from app.core import models

from app.services.mail_queue import process_mail_queue
from app.core.constants import MAIL_QUEUE_INTERVAL_SECONDS

logger = logging.getLogger(__name__)
_scheduler: Optional[BackgroundScheduler] = None

def _get_scheduler() -> BackgroundScheduler:
    """
    Initializes and returns a global `BackgroundScheduler` instance.

    This function ensures that there is a single instance of a `BackgroundScheduler`
    shared globally. If the scheduler has not been initialized yet, it creates a new
    instance, sets up necessary listeners, and assigns it to the global variable.

    Returns:
        BackgroundScheduler: The single instance of the global background scheduler.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    return _scheduler

def _on_job_event(event) -> None:
    """
    Handles job events during the scheduler's runtime.

    This function is used as a callback for job events, logging the outcome of each
    job based on whether it completed successfully or encountered an exception.

    Args:
        event: The event object containing details about the job execution, such
            as job ID and exception details.
    """
    if event.exception:
        logger.error(f"[Scheduler] Job {event.job_id} fehlgeschlagen.")
    else:
        logger.info(f"[Scheduler] Job {event.job_id} erfolgreich beendet.")

def start_scheduler() -> None:
    """
    Starts the task scheduler.
    """
    sched = _get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("[Scheduler] gestartet")

        # 📨 Mail-Queue-Worker hinzufügen
        try:
            sched.add_job(
                process_mail_queue,
                "interval",
                seconds=MAIL_QUEUE_INTERVAL_SECONDS,
                id="mail_queue_worker",
                replace_existing=True,
            )
            logger.info(f"[Scheduler] Mail-Queue-Worker alle {MAIL_QUEUE_INTERVAL_SECONDS}s aktiviert.")
        except Exception as e:
            logger.error(f"[Scheduler] Fehler beim Starten des Mail-Queue-Workers: {e}")

def stop_scheduler() -> None:
    """
    Stops the currently running scheduler, if active, without waiting for tasks to complete.

    This function retrieves the scheduler using an internal method and checks if it
    is currently running. If the scheduler is running, it is shutdown without
    waiting for currently scheduled tasks to complete. After shutdown, a log
    message is recorded to indicate that the scheduler has been stopped.

    Raises:
        Exception: If there are internal issues during scheduler shutdown.
    """
    sched = _get_scheduler()
    if sched.running:
        sched.shutdown(wait=False)
        logger.info("[Scheduler] gestoppt")

def _job_id(job_id: int) -> str:
    """
    Constructs a string identifier for a job using the provided job ID.

    Args:
        job_id (int): The ID of the job.

    Returns:
        str: The constructed job identifier string in the format "job_{job_id}".
    """
    return f"job_{job_id}"

def unschedule(job_id: int) -> None:
    """
    Unschedules a job that matches the given job ID.

    This function removes a job from the scheduler if it exists. The job is identified
    based on the provided job ID. After removal, a log entry is created to confirm
    the job has been removed.

    Args:
        job_id (int): The ID of the job to be removed from the scheduler.

    Returns:
        None
    """
    sched = _get_scheduler()
    job = sched.get_job(_job_id(job_id))
    if job:
        sched.remove_job(job.id)
        logger.info(f"[Scheduler] Job {job_id} entfernt")

def register_job(job: models.MailerJob) -> None:
    """
    Registers a job in the scheduler using specified job attributes. This function handles jobs
    with either a cron schedule or a specific one-time execution schedule. If a cron string or
    execution date is invalid, the job will not be scheduled.

    Args:
        job: The MailerJob instance representing the job to be scheduled.
            It must include an ID and definitions for its execution schedule
            (either as a cron string or a specific execution time).

    Raises:
        ValueError: Raised internally if the provided cron string is invalid or malformed.
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

        # Falls DB-naiv (keine tzinfo) → als UTC interpretieren
        if run_date.tzinfo is None:
            run_date = run_date.replace(tzinfo=timezone.utc)

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
    Resynchronizes all mailer jobs by registering each given job through the job registration
    process. This ensures all specified mailer jobs are synchronized and ready for dispatch.

    Args:
        jobs (list[models.MailerJob]): A list of MailerJob instances to be resynchronized.

    Returns:
        None
    """
    for j in jobs:
        register_job(j)

def get_scheduler() -> BackgroundScheduler:
    """
    Returns the active global BackgroundScheduler instance, initializing it if necessary.
    """
    return _get_scheduler()
