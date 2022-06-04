import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Literal, Sequence

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
    type: Literal["video"]
    width: int
    height: int
    variants: Sequence[MediaVideoItem]


class Includes:
    media: Sequence[MediaVideo | MediaPhoto]
    users: Sequence[User]
    tweets: Sequence[Tweet]


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
        return json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))

    async def users(self, *users) -> UsersResponse:
        response: httpx.Response = await self.__client.request(
            "GET",
            "https://api.twitter.com/2/users",
            params={
                "ids": users,
                "user.fields": ",".join(
                    ["name", "username", "profile_image_url", "protected"]
                ),
            },
        )
        return json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
