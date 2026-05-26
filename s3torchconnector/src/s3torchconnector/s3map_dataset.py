#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  // SPDX-License-Identifier: BSD
from functools import partial
from typing import List, Any, Callable, Iterable, Union, Optional
import logging

import torch.utils.data
from s3torchconnector._s3bucket_key_data import S3BucketKeyData

from ._s3client import S3Client, S3ClientConfig, resolve_s3client_config
from . import S3Reader, S3ReaderConstructor
from .s3reader import S3ReaderConstructorProtocol
from ._user_agent import UserAgent

from ._s3dataset_common import (
    get_objects_from_uris,
    get_objects_from_prefix,
    identity,
)

log = logging.getLogger(__name__)


class S3MapDataset(torch.utils.data.Dataset):
    """A Map-Style dataset created from S3 objects.

    To create an instance of S3MapDataset, you need to use
    `from_prefix` or `from_objects` methods.
    """

    def __init__(
        self,
        region: str,
        get_dataset_objects: Callable[[S3Client], Iterable[S3BucketKeyData]],
        endpoint: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        transform: Callable[[S3Reader], Any] = identity,
        s3client_config: Optional[S3ClientConfig] = None,
        reader_constructor: Optional[S3ReaderConstructorProtocol] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        self._get_dataset_objects = get_dataset_objects
        self._transform = transform
        self._region = region
        self._s3client_config = resolve_s3client_config(
            s3client_config,
            endpoint=endpoint,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        self._endpoint = self._s3client_config.endpoint_url
        self._client = None
        self._bucket_key_pairs: Optional[List[S3BucketKeyData]] = None
        self._reader_constructor = reader_constructor or S3ReaderConstructor.default()

    @property
    def region(self):
        return self._region

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def _dataset_bucket_key_pairs(self) -> List[S3BucketKeyData]:
        if self._bucket_key_pairs is None:
            self._bucket_key_pairs = list(self._get_dataset_objects(self._get_client()))
        assert self._bucket_key_pairs is not None
        return self._bucket_key_pairs

    @classmethod
    def from_objects(
        cls,
        object_uris: Union[str, Iterable[str]],
        *,
        region: str,
        endpoint: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        transform: Callable[[S3Reader], Any] = identity,
        s3client_config: Optional[S3ClientConfig] = None,
        reader_constructor: Optional[S3ReaderConstructorProtocol] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """Returns an instance of S3MapDataset using the S3 URI(s) provided.

        Args:
          object_uris(str | Iterable[str]): S3 URI of the object(s) desired.
          region(str): S3 region or provider-specific signing region used for requests.
            For S3-compatible object stores, this can be a value such as "auto" or "eu-north1".
          endpoint(str): Custom S3 endpoint for the bucket where the objects are stored.
            Prefer endpoint_url for new code.
          endpoint_url(str): Endpoint URL of an S3-compatible object store.
          transform: Optional callable which is used to transform an S3Reader into the desired type.
          s3client_config: Optional S3ClientConfig with parameters for S3 client.
          reader_constructor (Optional[S3ReaderConstructorProtocol]): Optional partial(S3Reader) created using S3ReaderConstructor
            e.g. S3ReaderConstructor.sequential() or S3ReaderConstructor.range_based()
          access_key_id(str): Static access key ID for S3 authentication.
          secret_access_key(str): Static secret access key for S3 authentication.

        Returns:
            S3MapDataset: A Map-Style dataset created from S3 objects.

        Raises:
            S3Exception: An error occurred accessing S3.
        """
        log.info(f"Building {cls.__name__} from_objects")
        return cls(
            region,
            partial(get_objects_from_uris, object_uris),
            endpoint,
            endpoint_url=endpoint_url,
            transform=transform,
            s3client_config=s3client_config,
            reader_constructor=reader_constructor,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )

    @classmethod
    def from_prefix(
        cls,
        s3_uri: str,
        *,
        region: str,
        endpoint: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        transform: Callable[[S3Reader], Any] = identity,
        s3client_config: Optional[S3ClientConfig] = None,
        reader_constructor: Optional[S3ReaderConstructorProtocol] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """Returns an instance of S3MapDataset using the S3 URI provided.

        Args:
          s3_uri(str): An S3 URI (prefix) of the object(s) desired. Objects matching the prefix will be included in the returned dataset.
          region(str): S3 region or provider-specific signing region used for requests.
            For S3-compatible object stores, this can be a value such as "auto" or "eu-north1".
          endpoint(str): Custom S3 endpoint for the bucket where the objects are stored.
            Prefer endpoint_url for new code.
          endpoint_url(str): Endpoint URL of an S3-compatible object store.
          transform: Optional callable which is used to transform an S3Reader into the desired type.
          s3client_config: Optional S3ClientConfig with parameters for S3 client.
          reader_constructor (Optional[S3ReaderConstructorProtocol]): Optional partial(S3Reader) created using S3ReaderConstructor
            e.g. S3ReaderConstructor.sequential() or S3ReaderConstructor.range_based()
          access_key_id(str): Static access key ID for S3 authentication.
          secret_access_key(str): Static secret access key for S3 authentication.

        Returns:
            S3MapDataset: A Map-Style dataset created from S3 objects.

        Raises:
            S3Exception: An error occurred accessing S3.
        """
        log.info(f"Building {cls.__name__} from_prefix {s3_uri=}")
        return cls(
            region,
            partial(get_objects_from_prefix, s3_uri),
            endpoint,
            endpoint_url=endpoint_url,
            transform=transform,
            s3client_config=s3client_config,
            reader_constructor=reader_constructor,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )

    def _get_client(self):
        if self._client is None:
            reader_type_string = S3ReaderConstructor.get_reader_type_string(
                self._reader_constructor
            )
            self._client = S3Client(
                self.region,
                user_agent=UserAgent(
                    comments=[f"md/dataset#map md/reader_type#{reader_type_string}"]
                ),
                s3client_config=self._s3client_config,
            )
        return self._client

    def _get_object(self, i: int) -> S3Reader:
        bucket_key = self._dataset_bucket_key_pairs[i]
        return self._get_client().get_object(
            bucket_key.bucket,
            bucket_key.key,
            object_info=bucket_key.object_info,
            reader_constructor=self._reader_constructor,
        )

    def __getitem__(self, i: int) -> Any:
        return self._transform(self._get_object(i))

    def __len__(self):
        return len(self._dataset_bucket_key_pairs)
