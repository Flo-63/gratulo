from datetime import date
import sys

from app.core.database import SessionLocal
from app.services.mailer_service import execute_job_by_id


def main():
    """
    Main entry point for executing a mailer job by job ID and optional logical date.

    This function determines the job to execute based on the provided command-line
    arguments and then initiates it. If no logical date is provided, it defaults
    to today's date. The script ensures correct command-line argument processing
    and provides error handling for invalid dates or improper usage. The database
    session is properly handled to ensure resources are cleaned up after execution.

    :param sys.argv: Command-line arguments input. Expected format:
                     python -m app.helpers.mailer_runner <job_id> [<yyyy-mm-dd>]
    :return: None
    """
    if len(sys.argv) < 2:
        print("Usage: python -m app.helpers.mailer_runner <job_id> [<yyyy-mm-dd>]")
        sys.exit(1)

    job_id = int(sys.argv[1])
    logical_date = date.today()

    if len(sys.argv) >= 3:
        try:
            logical_date = date.fromisoformat(sys.argv[2])
        except ValueError:
            print("❌ Ungültiges Datumsformat. Bitte yyyy-mm-dd verwenden.")
            sys.exit(1)

    db = SessionLocal()
    try:
        print(f"▶️  Starte Mailer-Job {job_id} für {logical_date.isoformat()} ...")
        execute_job_by_id(job_id, logical=logical_date)
        print("✅ Fertig.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
