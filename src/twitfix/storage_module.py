import os
import pathlib
import shutil
import urllib.request
from datetime import timedelta
from typing import Tuple
from uuid import UUID, uuid5

import requests

try:
    import google.auth
    import google.auth.compute_engine
    import google.cloud.storage
except:
    pass


class StorageBase:
    def __init__(self, config) -> None:
        self.config = config
        pass

    def store_media(self, url: str) -> Tuple[bool, str]:
        """
        Download the given url for rehosting by our own system.
        """
        pass

    def retrieve_media(self, own_identifier: str):
        """
        Retrieve a cached local version of the given URL
        """
        pass


class LocalFilesystem(StorageBase):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.basepath = pathlib.Path(config['config']['download_base'])


    def store_media(self, url: str):
        filename = (url.rsplit('/', 1)[-1].split('.mp4')[0] + '.mp4')

        PATH = (self.basepath / filename).resolve()
        if not PATH.is_relative_to(self.basepath):
            raise OSError("Invalid media identifier.")
        if PATH.exists() and PATH.is_file() and os.access(PATH, os.R_OK):
            print(" ➤ [[ FILE EXISTS ]]")
            return True, filename

        print(" ➤ [[ FILE DOES NOT EXIST, DOWNLOADING... ]]")
        mp4file = urllib.request.urlopen(url)
        with PATH.open('wb') as output:
            shutil.copyfileobj(mp4file, output)
        return False, filename


    def retrieve_media(self, own_identifier: str):
        PATH = (self.basepath / own_identifier).resolve()
        if not PATH.is_relative_to(self.basepath):
            raise OSError("Invalid media identifier.")
        if PATH.exists() and PATH.is_file() and os.access(PATH, os.R_OK):
            print(f' ➤ [[ PRESENTING FILE: {own_identifier!r}, URL: https://fxtwitter.com/media/{own_identifier} ]]')
            return {"output": "file", "content": PATH} # send_file accepts a path and will handle the file from there.
        return None


class GoogleCloudStorage(StorageBase):
    STORAGE_NAMESPACE = UUID("dbc14e27-a6ed-4343-98ef-285aa17cacfd")

    def __init__(self, config) -> None:
        bucket = config['config']['gcp_bucket']
        self.client = google.cloud.storage.Client()
        self.bucket = self.client.get_bucket(bucket)
        auth_request = requests.Request()
        credentials, project = google.auth.default()
        self.signing_credentials = google.auth.compute_engine.IDTokenCredentials(auth_request, "", service_account_email=credentials.service_account_email)


    def store_media(self, url: str) -> Tuple[bool, str]:
        name = str(uuid5(self.STORAGE_NAMESPACE, url))
        blob = self.bucket.blob(name, chunk_size=2**18)
        if blob.exists():
            return True, name
        else:
            mp4file = urllib.request.urlopen(url)
            mime = mp4file.getheader('content-type')
            url = blob.create_resumable_upload_session(mime)
            req = urllib.request.Request(url, mp4file, method='PUT', headers={"content-type": mime})
            urllib.request.urlopen(req, req.data)
        return False, name

    def retrieve_media(self, own_identifier: str):
        url = self.bucket.get_blob(own_identifier).generate_signed_url(
            timedelta(minutes=5), 
            credentials=self.signing_credentials, 
            version='v4'
        )
        return {"output": "url", "url": url}

class NoStorage(StorageBase):
    def store_media(self, url: str):
        return False, url
    
    def retrieve_media(self, own_identifier: str):
        return {"output": "url", "url": own_identifier}


def initialize_storage(storage_type: str, config) -> StorageBase:
    if storage_type == "local":
        return LocalFilesystem(config)

    if storage_type == "gcp_storage":
        return GoogleCloudStorage(config)

    if storage_type == "none":
        return NoStorage()
    
    raise LookupError(f"Unrecognized storage {storage_type}")