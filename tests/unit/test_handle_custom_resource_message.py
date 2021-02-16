from restrict_download_region import cfnresponse, restrict_region
from pytest_mock import MockerFixture
import pytest


def test_handle_custom_resource_message__successful_execution__not_custom_resource(mocker: MockerFixture):
    mock_cfn_send = mocker.patch.object(cfnresponse, "send", autospec=True)

    event = {}
    context = {}

    @restrict_region.handle_custom_resource_message(event, context)
    def stub_function():
        pass

    stub_function()

    assert not mock_cfn_send.called


def test_handle_custom_resource_message__failed_execution__not_custom_resource(mocker: MockerFixture):
    mock_cfn_send = mocker.patch.object(cfnresponse, "send", autospec=True)

    event = {""}
    context = {}

    @restrict_region.handle_custom_resource_message(event, context)
    def stub_function():
        raise Exception("failed")

    with pytest.raises(Exception):
        stub_function()

    assert not mock_cfn_send.called


def test_handle_custom_resource_message__successful_execution__is_custom_resource(mocker: MockerFixture):
    mock_cfn_send = mocker.patch.object(cfnresponse, "send", autospec=True)

    event = {"RequestType": "Create"}
    context = {}

    @restrict_region.handle_custom_resource_message(event, context)
    def stub_function():
        pass

    stub_function()

    mock_cfn_send.assert_called_once_with(event, context, cfnresponse.SUCCESS,
                                          restrict_region.empty_custom_resource_response_data)


def test_handle_custom_resource_message__failed_execution__is_custom_resource(mocker: MockerFixture):
    mock_cfn_send = mocker.patch.object(cfnresponse, "send", autospec=True)

    event = {"RequestType": "Create"}
    context = {}

    @restrict_region.handle_custom_resource_message(event, context)
    def stub_function():
        raise Exception("failed")

    with pytest.raises(Exception):
        stub_function()

    mock_cfn_send.assert_called_once_with(event, context, cfnresponse.FAILED,
                                          restrict_region.empty_custom_resource_response_data)
