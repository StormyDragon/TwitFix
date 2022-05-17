# TwitFix

Flask server that serves fixed twitter video embeds to desktop discord by using either the Twitter API or Youtube-DL to grab tweet video information. This also automatically embeds the first link in the text of non video tweets (API Only)

## How to use (discord side)

just put the url to the server, and directly after, the full URL to the tweet you want to embed

**This fork is running in a Google Cloud Run container**

```
https://ayytwitter.com/[twitter video url] or [last half of twitter url] (everything past twitter.com/)
```

You can also simply type out 'ayy' directly before 'twitter.com' in any valid twitter video url, and that will convert it into a working TwitFix url, pretend for example that fx is just ayy, well, you get the gist:

![example](example.gif)

## Robin Universe's Other Projects:

**Note**: If you enjoy this service, please considering donating via [Ko-Fi](https://ko-fi.com/robin_universe) as the original creator

[TwitFix-Bot](https://github.com/robinuniverse/TwitFix-Bot) - A discord bot for automatically converting normal twitter links posted by users into twitfix links

[TwitFix-Extension](https://github.com/robinuniverse/TwitFix-Extension) - A browser extention that lets you right click twitter videos to copy a twitfix link to your clipboard

## How to run

### `deploy/here`
* `systemd`
* `poetry`

This `deploy.sh` script installs a user service which runs as long as the user is logged in. Useful for testing. 
You may also follow directions for making the service linger. The configuration for `uwsgi` lives in `twitfix.ini`
this is the deployment method used by TwitFix originally.

I have included some files to give you a head start on setting this server up with uWSGI, though if you decide to use uWSGI I suggest you set up mongoDB link caching 

### `deploy/local`
* `docker`
* `docker-compose`

`docker-compose up` to launch everything; this is a blueprint using mongodb as the 
database and a dedicated volume as the download location.

### `deploy/gcp`
* `terraform`
* `gcloud`
* A project set up on google cloud platform.

This deployment script can be run with the following commands which will set up
a dedicated Cloud Run service with the Firestore database keeping the links and 
Google Cloud Storage to host files, handled by a dedicated limited service account.

```sh
terraform init
terraform apply -var-file template.tfvars
```

### Config

Configuration can be done through the environment by specifying the environment variable `CONFIG_FROM` with the value `environment`. Some sensible defaults have been added to the various deployment scripts.

```env
CONFIG_FROM=environment
TWITFIX_CONFIG_FROM="environment"
TWITFIX_STORAGE_MODULE="local_storage"
TWITFIX_LINK_CACHE= "json"
TWITFIX_DB="..."
TWITFIX_DB_TABLE="..."
TWITFIX_DOWNLOAD_METHOD="youtube-dl"
TWITFIX_COLOR="#43B581"
TWITFIX_APP_NAME="TwitFix"
TWITFIX_REPO="https://github.com/stormydragon/twitfix"
TWITFIX_BASE_URL="https://localhost:8080"
TWITFIX_DOWNLOAD_BASE="/tmp"
TWITFIX_TWITTER_API_KEY="..."
TWITFIX_TWITTER_API_SECRET="..."
TWITFIX_TWITTER_ACCESS_TOKEN="..."
TWITFIX_TWITTER_ACCESS_SECRET="..."
```

### Config (deprecated)

The older method of configuration relies on generating a config.json in the root directory
the first time you run it, the options are:

**API** - This will be where you put the credentials for your twitter API if you use this method

**database** - This is where you put the URL to your mongoDB database if you are using one

**link_cache** - (Options: **db**, **json**)

- **db**: Caches all links to a mongoDB database. This should be used it you are using uWSGI and are not just running the script on its own as one worker
- **json**: This saves cached links to a local **links.json** file

**method** - ( Options: **youtube-dl**, **api**, **hybrid** ) 

- **youtube-dl**: the original method for grabbing twitter video links, this uses a guest token provided via youtube-dl and should work well for individual instances, but may not scale up to a very large amount of usage

- **api**: this directly uses the twitter API to grab tweet info, limited to 900 calls per 15m
- **hybrid**: This will start off by using the twitter API to grab tweet info, but if the rate limit is reached or the api fails for any other reason it will switch over to youtube-dl to avoid downtime

**color** - Accepts a hex formatted color code, can change the embed color

**appname** - Can change the app name easily wherever it's shown

**repo** - used to change the repo url that some links redirect to

**url** - used to tell the user where to look for the oembed endpoint, make sure to set this to your public facing url

This project is licensed under the **Do What The Fuck You Want Public License**
