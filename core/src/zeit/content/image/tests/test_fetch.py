import pytest
import shutil
from os import path
from pytest_server_fixtures.http import SimpleHTTPTestServer
from zeit.content.image import fetch


@pytest.yield_fixture
def image_server():
    image_dir = path.abspath(path.join(path.dirname(__file__), '..', 'browser', 'testdata'))
    with SimpleHTTPTestServer() as s:
        shutil.copytree(image_dir, path.join(s.document_root, "testdata"))
        s.start()
        yield s


def test_image_server(image_server):
    response = image_server.get('/testdata/opernball.jpg')
    assert response.status_code == 200


def test_fetch_remote_image(image_server):
    local_image = fetch.get_remote_image('%s/testdata/opernball.jpg' % image_server.uri)
    assert local_image.mimeType == 'image/jpeg'
