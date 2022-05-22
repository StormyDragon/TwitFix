import multiprocessing
import os

from .routes import app


def main():
    workers = multiprocessing.cpu_count()
    port = os.environ.get("PORT", None)
    app.run(host="0.0.0.0", port=port, workers=workers, debug=False)


if __name__ == "__main__":
    main()
