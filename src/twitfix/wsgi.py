import multiprocessing
import os

from .routes import app

if app.config.get('DEPLOY_TARGET') == 'GCP':
    import google.cloud.logging_v2

    from .cloud_logging import initialize_app as init_cloud_logging
    client = google.cloud.logging_v2.Client()
    client.setup_logging()
    init_cloud_logging(app)
else:
    import logging
    logging.basicConfig()


def main():
    workers = multiprocessing.cpu_count()
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, workers=workers, debug=False, access_log=False)


if __name__ == "__main__":
    main()
