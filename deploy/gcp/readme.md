# Deployment to Google Cloud Platform

## Register with google cloud
* [Google Cloud](https://cloud.google.com/)
* [Firebase](https://firebase.google.com/)

## Prepare the project
* Attach a billing account (or if going via Firebase use the Blaze plan)
* Choose your deployment region, zone and database location
* Override configuration for twitfix in the `secret-config.json` file.
* Install Terraform
* Run terraform init

## Install the project
* Run terraform apply with your chosen variables.
* When the service has been deployed you may check out [Domain Mappings](https://console.cloud.google.com/run/domains)

```
terraform init

terraform apply \
    -var=google_cloud_project=--my-twitfix-project \
    -var=google_cloud_region=europe-west1 \
    -var=google_cloud_zone=europe-west1-b \
    -var=google_app_engine_location=europe-west

```
