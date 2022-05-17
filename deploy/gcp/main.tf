variable "google_cloud_project" {
  type        = string
  description = "Pre-existing google cloud project into which to deploy."
}

# https://cloud.google.com/run/docs/locations
# https://cloud.google.com/run/docs/mapping-custom-domains#limitations
variable "google_cloud_region" {
  type = string
}

variable "google_app_engine_location" {
  type        = string
  description = "Where to locate the firestore instance us-central OR europe-west"
}

# https://cloud.google.com/compute/docs/regions-zones/#available 
variable "google_cloud_zone" {
  type = string
}

variable "twitfix_config_file" {
  type    = string
  default = "secret-config.json"
}

resource "google_service_account" "twitfix" {
  account_id   = "twitfix-service-account"
  display_name = "Service Account For Run Service"
}

resource "google_storage_bucket_iam_member" "storage_permission" {
  bucket = google_storage_bucket.media_store.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.twitfix.email}"
}

resource "google_project_iam_member" "firestore_permission" {
  project = var.google_cloud_project
  role    = "roles/datastore.user"

  member  = "serviceAccount:${google_service_account.twitfix.email}"
}

resource "google_project_iam_member" "token_signer_permission" {
  project = var.google_cloud_project
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.twitfix.email}"
}

resource "google_storage_bucket" "media_store" {
  name = "${var.google_cloud_project}-media-bucket"
  # https://cloud.google.com/storage/docs/locations
  # https://cloud.google.com/storage/pricing#storage-pricing
  location      = var.google_cloud_region
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 15
    }
    action {
      type = "Delete"
    }
  }
}

locals {
  default_config = {
    "TWITFIX_CONFIG_FROM"           = "environment"
    "TWITFIX_STORAGE_MODULE"        = "gcp_storage"
    "TWITFIX_STORAGE_BUCKET"        = google_storage_bucket.media_store.name
    "TWITFIX_LINK_CACHE"            = "firestore"
    "TWITFIX_DB"                    = "[keep-in-secret-file]"
    "TWITFIX_DB_TABLE"              = "[keep-in-secret-file]"
    "TWITFIX_DOWNLOAD_METHOD"       = "youtube-dl"
    "TWITFIX_COLOR"                 = "#43B581"
    "TWITFIX_APP_NAME"              = "TwitFix"
    "TWITFIX_REPO"                  = "https://github.com/robinuniverse/twitfix"
    "TWITFIX_BASE_URL"              = "https://localhost:8080"
    "TWITFIX_DOWNLOAD_BASE"         = "/tmp"
    "TWITFIX_TWITTER_API_KEY"       = "[keep-in-secret-file]"
    "TWITFIX_TWITTER_API_SECRET"    = "[keep-in-secret-file]"
    "TWITFIX_TWITTER_ACCESS_TOKEN"  = "[keep-in-secret-file]"
    "TWITFIX_TWITTER_ACCESS_SECRET" = "[keep-in-secret-file]"
  }
  config               = merge(local.default_config, jsondecode(data.local_file.config.content))
  project_source_path  = abspath("${path.cwd}/../../src")
  docker_registry      = "${var.google_cloud_region}-docker.pkg.dev"
  google_artifact_repo = "${local.docker_registry}/${var.google_cloud_project}/${google_artifact_registry_repository.twitfix-repo.repository_id}"
}

data "local_file" "config" {
  filename = var.twitfix_config_file
}

########################################################################################

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "2.16.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
  registry_auth {
    address = local.docker_registry
    config_file_content = jsonencode({
      credHelpers = {
        "${local.docker_registry}" = "gcloud"
      }
    })
  }
}

provider "google" {
  project = var.google_cloud_project
  region  = var.google_cloud_region
  zone    = var.google_cloud_zone
}

provider "google-beta" {
  project = var.google_cloud_project
  region  = var.google_cloud_region
  zone    = var.google_cloud_zone
}

### Required services

resource "google_project_service" "artifact_registry" {
  project            = var.google_cloud_project
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  project            = var.google_cloud_project
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_app_engine_application" "app_engine" {
  project       = var.google_cloud_project
  location_id   = var.google_app_engine_location
  database_type = "CLOUD_FIRESTORE"
}

### Repository

resource "google_artifact_registry_repository" "twitfix-repo" {
  provider = google-beta
  depends_on = [
    google_project_service.artifact_registry,
    google_project_service.run,
    google_app_engine_application.app_engine
  ]

  location      = var.google_cloud_region
  repository_id = "twitfix-repository"
  description   = "stores images for twitfix"
  format        = "DOCKER"
}

### Docker Image build and push

resource "random_string" "random" {
  length  = 8
  special = false
  keepers = {
    python_files = sha1(join("", [for f in fileset(local.project_source_path, "twitfix/*.py") : filesha1("${local.project_source_path}/${f}")]))
    poetry       = sha1(join("", [for f in fileset(local.project_source_path, "{poetry.lock,poetry.toml,pyproject.toml}") : filesha1("${local.project_source_path}/${f}")]))
    static       = sha1(join("", [for f in fileset(local.project_source_path, "static/*") : filesha1("${local.project_source_path}/${f}")]))
    templates    = sha1(join("", [for f in fileset(local.project_source_path, "templates/*") : filesha1("${local.project_source_path}/${f}")]))
  }
}

resource "docker_registry_image" "twitfix-image" {
  name = "${local.google_artifact_repo}/twitfix-gcp-cloudrun:${random_string.random.result}"

  lifecycle {
    create_before_destroy = true
  }

  build {
    context = local.project_source_path
    build_args = {
      EXTRAS = "deploy-gcp"
    }
  }
}

### Run the service

resource "google_cloud_run_service_iam_member" "member" {
  project  = google_cloud_run_service.twitfix-run-service.project
  location = google_cloud_run_service.twitfix-run-service.location
  service  = google_cloud_run_service.twitfix-run-service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service" "twitfix-run-service" {
  name       = "twitfix-service"
  project    = var.google_cloud_project
  location   = var.google_cloud_region
  depends_on = [google_project_service.run]


  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = 1
        "autoscaling.knative.dev/maxScale" = 100
      }
    }
    spec {
      service_account_name  = google_service_account.twitfix.email
      container_concurrency = 1000
      containers {
        image = docker_registry_image.twitfix-image.name
        dynamic "env" {
          for_each = [for v in keys(local.config) : { key = v, value = local.config[v] }]
          content {
            name  = env.value.key
            value = env.value.value
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
