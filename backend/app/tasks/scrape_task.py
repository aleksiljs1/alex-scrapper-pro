import docker
import glob
import os
from datetime import datetime, timedelta

from bson import ObjectId
from app.tasks.celery_app import celery_app
from app.config import settings
from app.services.queue_service import publish_status


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def scrape_profile(self, profile_id: str, url: str):
    """
    1. Update status to 'processing'
    2. Run the scraper bot via Docker SDK exec
    3. Find the output JSON
    4. Chain to ingest task
    """
    from app.db.mongodb import get_sync_collection

    collection = get_sync_collection("profiles")

    try:
        # Mark as processing
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {"status": "processing", "updated_at": datetime.utcnow()}},
        )
        publish_status(profile_id, url, "processing")

        # Record existing JSON files before scraping (to find the new one after)
        output_dir = os.path.join(
            settings.SHARED_VOLUME_PATH, "scraped_data_output", "profile"
        )
        os.makedirs(output_dir, exist_ok=True)
        existing_files = set(glob.glob(os.path.join(output_dir, "profile_*.json")))

        # Execute the scraper bot via Docker SDK
        client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        container = client.containers.get(settings.SCRAPER_CONTAINER_NAME)
        exec_result = container.exec_run(
            cmd=["/python/bin/python", "/app/run_scrape.py", url],
            environment={
                "DISPLAY": ":1",
                "HOME": "/root",
                "FB_USERNAME": settings.FB_USERNAME,
                "FB_PASSWORD": settings.FB_PASSWORD,
            },
            demux=True,
        )

        stdout = (exec_result.output[0] or b"").decode()
        stderr = (exec_result.output[1] or b"").decode()

        if exec_result.exit_code != 0:
            raise Exception(
                f"Scraper failed (exit {exec_result.exit_code}): {stderr or stdout}"
            )

        # Find new JSON file
        current_files = set(glob.glob(os.path.join(output_dir, "profile_*.json")))
        new_files = current_files - existing_files

        if not new_files:
            raise Exception("No output JSON file found after scraping")

        json_file = max(new_files, key=os.path.getmtime)  # newest file

        # Chain to ingest task
        from app.tasks.ingest_task import ingest_profile_json

        ingest_profile_json.delay(profile_id, url, json_file)

    except Exception as exc:
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        publish_status(profile_id, url, "failed")
        raise self.retry(exc=exc)


@celery_app.task
def cleanup_stale():
    """Find profiles stuck in 'processing' for >10 minutes and reset to 'queued'."""
    from app.db.mongodb import get_sync_collection

    collection = get_sync_collection("profiles")
    threshold = datetime.utcnow() - timedelta(minutes=10)

    result = collection.update_many(
        {"status": "processing", "updated_at": {"$lt": threshold}},
        {"$set": {"status": "queued", "updated_at": datetime.utcnow()}},
    )

    if result.modified_count > 0:
        print(f"Reset {result.modified_count} stale processing profiles to queued")
