from pytest_mock import MockerFixture
import restrict_download_region.restrict_region as restrict_region
import pytest
import requests
import json
import pkg_resources


@pytest.mark.parametrize("region, expected", [
    ('us-east-1', ['15.230.56.104/31', '2600:1f19:8000::/36']),
    ('eu-west-2', ['52.93.153.170/32', '2a05:d07a:c000::/40'])])
def test_get_ip_prefixes_for_region(mocker: MockerFixture, region, expected):
    mock_requests_get = mocker.patch.object(requests, "get", autospec=True)
    mock_requests_get.return_value.json.return_value = json.load(
        open(pkg_resources.resource_filename(__name__, 'sample_ip_ranges.json')))

    mocker.patch.object(restrict_region, 'REGION', region)

    assert restrict_region.get_ip_prefixes_for_region() == expected


def test_get_ip_prefixes_for_region__REGION_not_set(mocker: MockerFixture):
    mocker.patch.object(restrict_region, 'REGION', None)

    with pytest.raises(ValueError):
        restrict_region.get_ip_prefixes_for_region()
