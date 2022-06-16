import os
import uuid
from typing import List

import requests
import twitter

TWITFIX_DOMAIN = "ayytwitter.com"
PLACEHOLDER_IMG_LINK = "https://picsum.photos/200"
PLACEHOLDER_VID_LINK = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
PLACEHOLDER_GIF_LINK = "https://i.imgur.com/T8zETAU.gif"

TWITFIX_TWITTER_API_KEY = os.getenv("TWITFIX_TWITTER_API_KEY")
TWITFIX_TWITTER_API_SECRET = os.getenv("TWITFIX_TWITTER_API_SECRET")


def post_tweet(
        t: twitter.Twitter,
        msg: str,
        media_ids: List[str] = None,
        *,
        sensitive: bool = False,
) -> int:
    media_ids = media_ids or []
    resp = t.statuses.update(
        status=msg,
        media_ids=",".join(media_ids),
        possibly_sensitive=sensitive,
    )
    return resp["id"]


def upload_media(t_up: twitter.Twitter, file_data: bytes) -> str:
    img_resp = t_up.media.upload(media=file_data)
    img_id = img_resp["media_id_string"]
    t_up.media.metadata.create(media_id=img_id, text="Placeholder image")
    return img_id


def upload_chunked_media(t_up: twitter.Twitter, file_data: bytes, media_type: str, media_category: str) -> str:
    chunk_size = 1024 * 1024
    total_bytes = len(file_data)
    segments = ((total_bytes - 1) // chunk_size) + 1
    resp = t_up.media.upload(
        command="INIT",
        total_bytes=total_bytes,
        media_type=media_type,
        media_category=media_category
    )
    media_id = resp["media_id"]
    for segment in range(segments):
        chunk = file_data[segment*chunk_size: (segment+1)*chunk_size]
        t_up.media.upload(command="APPEND", media_id=media_id, media=chunk, segment_index=segment)
    t_up.media.upload(command="FINALIZE", media_id=media_id)
    return str(media_id)


def format_links(tweet_id: int) -> List[str]:
    return [
        f"https://twitter.com/user/status/{tweet_id}",
        f"https://{TWITFIX_DOMAIN}/user/status/{tweet_id}"
    ]


def print_links(tweet_id: int) -> None:
    print("\n".join(format_links(tweet_id)))


def fetch_img_data() -> bytes:
    return requests.get(PLACEHOLDER_IMG_LINK).content


def fetch_vid_data() -> bytes:
    return requests.get(PLACEHOLDER_VID_LINK).content


def fetch_gif_data() -> bytes:
    return requests.get(PLACEHOLDER_GIF_LINK).content


def fetch_place_id(t: twitter.Twitter) -> str:
    resp = t.geo.reverse_geocode(lat=51.5007, long=0.1246)
    return resp["result"]["places"][0]["id"]


def upload_placeholder_images(t_up: twitter.Twitter, count: int = 1) -> List[str]:
    return [
        upload_media(t_up, fetch_img_data())
        for _ in range(count)
    ]


def upload_placeholder_vid(t_up: twitter.Twitter) -> str:
    vid_data = fetch_vid_data()
    return upload_chunked_media(t_up, vid_data, "video/mp4", "tweet_video")


def upload_placeholder_gif(t_up: twitter.Twitter) -> str:
    gif_data = fetch_gif_data()
    return upload_chunked_media(t_up, gif_data, "image/gif", "tweet_gif")


def post_example_tweets(t: twitter.Twitter, t_upload: twitter.Twitter):
    # Generate unique string
    unique_str = str(uuid.uuid4())
    # Post Text tweet
    print("Text tweet:")
    print_links(post_tweet(t, f"An example text tweet: {unique_str}"))
    # Post image tweet
    print("Single image tweet:")
    media_ids = upload_placeholder_images(t_upload, 1)
    print_links(post_tweet(t, f"An example image tweet: {unique_str}", media_ids))
    # Post a tweet with multiple images
    print("Multiple image tweet:")
    media_ids = upload_placeholder_images(t_upload, 4)
    print_links(post_tweet(t, f"An example tweet with multiple images: {unique_str}", media_ids))
    # Post sensitive image tweet
    print("Single image tweet:")
    media_ids = upload_placeholder_images(t_upload, 1)
    print_links(post_tweet(t, f"An example image tweet: {unique_str}", media_ids, sensitive=True))
    # Post a tweet with a video
    print("Video tweet:")
    media_ids = [upload_placeholder_vid(t_upload)]
    print_links(post_tweet(t, f"An example tweet with a video: {unique_str}", media_ids))
    # Post a tweet with a gif
    print("Gif tweet:")
    media_ids = [upload_placeholder_gif(t_upload)]
    print_links(post_tweet(t, f"An example tweet with a gif: {unique_str}", media_ids))
    # TODO: Place tweet
    # TODO: User profile tweet


if __name__ == "__main__":
    access_token = os.getenv("TWITFIX_TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITFIX_TWITTER_ACCESS_SECRET")
    if not access_token or not access_secret:
        access = twitter.oauth_dance("Twitfix QA tweet generator", TWITFIX_TWITTER_API_KEY, TWITFIX_TWITTER_API_SECRET)
        access_token, access_secret = access
    auth = twitter.OAuth(
        access_token,
        access_secret,
        TWITFIX_TWITTER_API_KEY,
        TWITFIX_TWITTER_API_SECRET
    )
    twit = twitter.Twitter(auth=auth)
    twit_upload = twitter.Twitter(domain="upload.twitter.com", auth=auth)
    # Check twitter login
    twit.statuses.home_timeline(count=2)
    # Post example tweets
    post_example_tweets(twit, twit_upload)
