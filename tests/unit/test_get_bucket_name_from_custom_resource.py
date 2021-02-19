import restrict_download_region.restrict_region as restrict_region
import pytest


def test_getbucket_name_from_custom_resource__no_bucket_name():
    with pytest.raises(ValueError):
        restrict_region.get_bucket_name_from_custom_resouce({})
    with pytest.raises(ValueError):
        restrict_region.get_bucket_name_from_custom_resouce({'ResourceProperties': {}})
    with pytest.raises(ValueError):
        restrict_region.get_bucket_name_from_custom_resouce({'ResourceProperties': {'KetbuckName': 'foobar'}})


def test_getbucket_name_from_custom_resource__with_bucket_name():
    assert restrict_region.get_bucket_name_from_custom_resouce(
        {'ResourceProperties': {'BucketName': 'foobar'}}) == 'foobar'
