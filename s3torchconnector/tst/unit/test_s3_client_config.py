#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  // SPDX-License-Identifier: BSD
import pytest
from hypothesis import given, example
from hypothesis.strategies import integers, floats

from s3torchconnector import S3ClientConfig
from s3torchconnector._s3client import resolve_s3client_config
from .test_s3_client import MiB, GiB


def test_default():
    config = S3ClientConfig()
    assert config.part_size == 8 * MiB
    assert config.throughput_target_gbps == 10.0
    assert config.force_path_style is False
    assert config.max_attempts == 10
    assert config.profile is None
    assert config.access_key_id is None
    assert config.secret_access_key is None
    assert config.endpoint_url is None


def test_enable_force_path_style():
    config = S3ClientConfig(force_path_style=True)
    assert config.force_path_style is True


def test_change_profile():
    config = S3ClientConfig(profile="test_profile")
    assert config.profile == "test_profile"


def test_static_credentials():
    config = S3ClientConfig(
        access_key_id="test-access-key-id",
        secret_access_key="test-secret-access-key",
    )
    assert config.access_key_id == "test-access-key-id"
    assert config.secret_access_key == "test-secret-access-key"
    assert "test-secret-access-key" not in repr(config)


def test_endpoint_url():
    config = S3ClientConfig(endpoint_url="https://s3-compatible.example.com")
    assert config.endpoint_url == "https://s3-compatible.example.com"


def test_resolve_s3client_config_direct_args():
    config = resolve_s3client_config(
        endpoint_url="https://s3-compatible.example.com",
        access_key_id="test-access-key-id",
        secret_access_key="test-secret-access-key",
        part_size=64 * MiB,
        force_path_style=True,
    )
    assert config.endpoint_url == "https://s3-compatible.example.com"
    assert config.access_key_id == "test-access-key-id"
    assert config.secret_access_key == "test-secret-access-key"
    assert config.part_size == 64 * MiB
    assert config.force_path_style is True


def test_resolve_s3client_config_direct_args_override_config():
    config = resolve_s3client_config(
        S3ClientConfig(
            endpoint_url="https://config.example.com",
            access_key_id="config-access-key-id",
            secret_access_key="config-secret-access-key",
        ),
        endpoint_url="https://direct.example.com",
        access_key_id="direct-access-key-id",
        secret_access_key="direct-secret-access-key",
        part_size=64 * MiB,
        force_path_style=True,
    )
    assert config.endpoint_url == "https://direct.example.com"
    assert config.access_key_id == "direct-access-key-id"
    assert config.secret_access_key == "direct-secret-access-key"
    assert config.part_size == 64 * MiB
    assert config.force_path_style is True


def test_resolve_s3client_config_endpoint_alias():
    config = resolve_s3client_config(endpoint="https://s3-compatible.example.com")
    assert config.endpoint_url == "https://s3-compatible.example.com"


def test_resolve_s3client_config_endpoint_alias_matches_endpoint_url():
    config = resolve_s3client_config(
        endpoint="https://s3-compatible.example.com",
        endpoint_url="https://s3-compatible.example.com",
    )
    assert config.endpoint_url == "https://s3-compatible.example.com"


def test_resolve_s3client_config_endpoint_alias_conflicts_with_endpoint_url():
    with pytest.raises(ValueError, match="endpoint_url"):
        resolve_s3client_config(
            endpoint="https://legacy.example.com",
            endpoint_url="https://direct.example.com",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"access_key_id": "test-access-key-id"},
        {"secret_access_key": "test-secret-access-key"},
        {"access_key_id": "", "secret_access_key": "test-secret-access-key"},
        {"access_key_id": "test-access-key-id", "secret_access_key": ""},
    ],
)
def test_invalid_static_credentials(kwargs):
    with pytest.raises(ValueError):
        S3ClientConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "access_key_id": "test-access-key-id",
            "secret_access_key": "test-secret-access-key",
            "profile": "test-profile",
        },
        {
            "access_key_id": "test-access-key-id",
            "secret_access_key": "test-secret-access-key",
            "unsigned": True,
        },
    ],
)
def test_static_credentials_cannot_be_combined_with_other_auth_modes(kwargs):
    with pytest.raises(ValueError):
        S3ClientConfig(**kwargs)


@given(part_size=integers(min_value=5 * MiB, max_value=5 * GiB))
def test_part_size_setup(part_size: int):
    config = S3ClientConfig(part_size=part_size)
    assert config.part_size == part_size
    assert config.throughput_target_gbps == 10.0


@given(throughput_target_gbps=floats(min_value=1.0, max_value=100.0))
def test_throughput_target_gbps_setup(throughput_target_gbps: float):
    config = S3ClientConfig(throughput_target_gbps=throughput_target_gbps)
    assert config.part_size == 8 * 1024 * 1024
    assert config.throughput_target_gbps == throughput_target_gbps


@given(max_attempts=integers(min_value=1, max_value=10))
def test_max_attempts_setup(max_attempts: int):
    config = S3ClientConfig(max_attempts=max_attempts)
    assert config.max_attempts == max_attempts


@given(
    part_size=integers(min_value=5 * MiB, max_value=5 * GiB),
    throughput_target_gbps=floats(min_value=1.0, max_value=100.0),
    max_attempts=integers(min_value=1, max_value=10),
)
@example(part_size=5 * MiB, throughput_target_gbps=10.0, max_attempts=2)
@example(part_size=5 * GiB, throughput_target_gbps=15.0, max_attempts=8)
def test_custom_setup(part_size: int, throughput_target_gbps: float, max_attempts: int):
    config = S3ClientConfig(
        part_size=part_size,
        throughput_target_gbps=throughput_target_gbps,
        max_attempts=max_attempts,
    )
    assert config.part_size == part_size
    assert config.throughput_target_gbps == throughput_target_gbps
    assert config.max_attempts == max_attempts
