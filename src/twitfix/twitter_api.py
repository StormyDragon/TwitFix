import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Dict, Literal, Sequence, Tuple

import httpx

TWITTER_CREDENTIAL_REFRESH = timedelta(minutes=110)


class User:
    id: str
    username: str
    name: str
    profile_image_url: str
    protected: bool


class TweetReference:
    type: str
    id: str  # Tweet ID


class TweetAttachments:
    media_keys: Sequence[str]  # Media IDs


class Tweet:
    text: str
    id: str
    in_reply_to_user_id: str | None
    lang: str
    author_id: str
    possibly_sensitive: bool
    display_text_range: Tuple[int, int]
    referenced_tweets: Sequence[TweetReference]
    attachments: TweetAttachments
    created_at: str  # ISO datetime


class MediaVideoItem:
    bit_rate: int
    content_type: str
    url: str


class MediaPhoto:
    media_key: str
    type: Literal["photo"]
    width: int
    height: int
    url: str


class MediaVideo:
    media_key: str
    type: Literal["video", "animated_gif"]
    width: int
    height: int
    variants: Sequence[MediaVideoItem]


class Includes:
    media: Dict[str, MediaVideo | MediaPhoto]
    users: Dict[str, User]
    tweets: Dict[str, Tweet]


class TweetsResponse:
    data: Sequence[Tweet]
    includes: Includes


class UsersResponse:
    data: Sequence[User]


def credentialed_client(api_key: str, api_secret: str):
    token: str
    expires: datetime = datetime.now()
    client = httpx.AsyncClient()

    async def token_auth(request):
        nonlocal token, expires
        if expires < datetime.now():
            res = await client.post(
                "https://api.twitter.com/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(api_key, api_secret),
            )
            expires = datetime.now() + TWITTER_CREDENTIAL_REFRESH
            res.raise_for_status()
            token = res.json()["access_token"]

        request.headers.update({"Authorization": f"Bearer {token}"})

    return httpx.AsyncClient(event_hooks={"request": [token_auth]})


def convert_tweets_lists_to_map(obj):
    # convert data
    obj.data = {i["id"]: i for i in obj.data}
    # convert media
    obj.includes.media = {i["media_key"]: i for i in obj.includes.media or []}
    # convert users
    obj.includes.users = {i["id"]: i for i in obj.includes.users or []}
    # convert extra tweets
    obj.includes.tweets = {i["id"]: i for i in obj.includes.tweets or []}
    return obj


def convert_users_lists_to_map(obj):
    # convert data
    obj.data = {i["id"]: i for i in obj.data}
    return obj


class Twitter:
    __client: httpx.AsyncClient

    @classmethod
    def from_credentials(cls, api_key: str, api_secret: str):
        instance = cls()
        instance.__client = credentialed_client(api_key, api_secret)
        return instance

    @property
    async def token(self):
        pass

    async def tweets(self, *ids) -> TweetsResponse:
        response: httpx.Response = await self.__client.request(
            "GET",
            "https://api.twitter.com/2/tweets",
            params={
                "ids": ",".join(ids),
                "expansions": ",".join(
                    [
                        "author_id",
                        "attachments.media_keys",
                        "referenced_tweets.id",
                        "in_reply_to_user_id",
                    ]
                ),
                "tweet.fields": ",".join(
                    [
                        "created_at",
                        "attachments",
                        "referenced_tweets",
                        "possibly_sensitive",
                        "display_text_range",
                        "lang",
                    ]
                ),
                "user.fields": ",".join(
                    [
                        "name",
                        "username",
                        "profile_image_url",
                        "protected",
                    ]
                ),
                "media.fields": ",".join(
                    [
                        "media_key",
                        "type",
                        "duration_ms",
                        "height",
                        "width",
                        "variants",
                    ]
                ),
            },
        )
        output = json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
        return convert_tweets_lists_to_map(output)

    async def users(self, *users) -> UsersResponse:
        response: httpx.Response = await self.__client.request(
            "GET",
            "https://api.twitter.com/2/users",
            params={
                "ids": ",".join(users),
                "user.fields": ",".join(
                    ["name", "username", "profile_image_url", "protected"]
                ),
            },
        )
        output = json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
        return convert_users_lists_to_map(output)
