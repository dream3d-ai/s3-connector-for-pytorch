#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  // SPDX-License-Identifier: BSD
from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class S3ClientConfig:
    """A dataclass exposing configurable parameters for the S3 client.

    Args:
    throughput_target_gbps(float): Throughput target in Gigabits per second (Gbps) that we are trying to reach.
        10.0 Gbps by default (may change in future).
    part_size(int): Size (bytes) of file parts that will be uploaded/downloaded.
        Note: for saving checkpoints, the inner client will adjust the part size to meet the service limits.
        (max number of parts per upload is 10,000, minimum upload part size is 5 MiB).
        Part size must have values between 5MiB and 5GiB.
        8MiB by default (may change in future).
    unsigned(bool): Set to true to disable signing S3 requests.
    force_path_style(bool): forceful path style addressing for S3 client.
    max_attempts(int): amount of retry attempts for retrieable errors.
    profile(str): Profile name to use for S3 authentication.
    access_key_id(str): Static access key ID for S3 authentication.
    secret_access_key(str): Static secret access key for S3 authentication.
    endpoint_url(str): Endpoint URL for an S3-compatible object store.
    """

    throughput_target_gbps: float = 10.0
    part_size: int = 8 * 1024 * 1024
    unsigned: bool = False
    force_path_style: bool = False
    max_attempts: int = 10
    profile: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = field(default=None, repr=False)
    endpoint_url: Optional[str] = None

    def __post_init__(self):
        has_access_key_id = self.access_key_id is not None
        has_secret_access_key = self.secret_access_key is not None
        has_static_credentials = has_access_key_id or has_secret_access_key

        if has_access_key_id != has_secret_access_key:
            raise ValueError(
                "access_key_id and secret_access_key must be provided together"
            )
        if has_static_credentials and (
            self.access_key_id == "" or self.secret_access_key == ""
        ):
            raise ValueError("access_key_id and secret_access_key must be non-empty")
        if has_static_credentials and self.profile is not None:
            raise ValueError("static credentials cannot be combined with profile")
        if has_static_credentials and self.unsigned:
            raise ValueError("static credentials cannot be combined with unsigned=True")


def resolve_s3client_config(
    s3client_config: Optional[S3ClientConfig] = None,
    *,
    endpoint: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    access_key_id: Optional[str] = None,
    secret_access_key: Optional[str] = None,
) -> S3ClientConfig:
    """Merge direct S3 connection arguments into S3ClientConfig.

    Direct arguments override matching fields in ``s3client_config``. ``endpoint`` is a
    backwards-compatible alias for ``endpoint_url``.
    """
    legacy_endpoint = endpoint or None
    direct_endpoint_url = endpoint_url or None

    if (
        legacy_endpoint is not None
        and direct_endpoint_url is not None
        and legacy_endpoint != direct_endpoint_url
    ):
        raise ValueError(
            "endpoint and endpoint_url cannot both be set to different values"
        )

    config = s3client_config or S3ClientConfig()
    return replace(
        config,
        endpoint_url=(
            direct_endpoint_url
            if direct_endpoint_url is not None
            else legacy_endpoint if legacy_endpoint is not None else config.endpoint_url
        ),
        access_key_id=(
            access_key_id if access_key_id is not None else config.access_key_id
        ),
        secret_access_key=(
            secret_access_key
            if secret_access_key is not None
            else config.secret_access_key
        ),
    )
