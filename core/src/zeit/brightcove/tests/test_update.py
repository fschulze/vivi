from datetime import datetime
from os import path
from unittest import mock
from zeit.brightcove.update import import_video, import_playlist
from zeit.cms.interfaces import ICMSContent
import pkg_resources
import pytz
import shutil
import transaction
import zeit.brightcove.testing
import zeit.cms.content.interfaces
import zeit.cms.workflow.interfaces
import zeit.content.image.testing
import zeit.content.video.video
import zope.security.management


def create_video():
    bc = zeit.brightcove.convert.Video()
    bc.data = {
        'id': 'myvid',
        'name': 'title',
        'created_at': '2017-05-15T08:24:55.916Z',
        'updated_at': '2017-05-16T08:24:55.916Z',
        'state': 'ACTIVE',
        'custom_fields': {},
        "images": {
            "poster": {
                "src": "nosuchhost"
            },
            "thumbnail": {
                "src": "nosuchhost"
            }
        },
    }
    return bc


class ImportVideoTest(zeit.brightcove.testing.FunctionalTestCase):

    def test_new_video_should_be_added_to_cms(self):
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/2017-05/myvid', None))
        import_video(create_video())
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual('title', video.title)
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        self.assertEqual(True, info.published)

    def test_new_video_should_create_empty_still_image_group(self):
        import_video(create_video())
        assert self.repository['video']['2017-05']['myvid'].video_still is None
        assert self.repository['video']['2017-05']['myvid-still'] is not None

    def test_new_video_should_create_empty_still_image_group_for_missing_src(self):
        video = create_video()
        del video.data['images']
        import_video(video)
        assert self.repository['video']['2017-05']['myvid'].video_still is None
        assert self.repository['video']['2017-05']['myvid-still'] is not None

    def test_new_video_should_create_empty_thumbnail_image_group(self):
        import_video(create_video())
        assert self.repository['video']['2017-05']['myvid'].thumbnail is None
        assert self.repository['video']['2017-05']['myvid-thumbnail'] is not None

    def test_changed_video_should_be_written_to_cms(self):
        bc = create_video()
        import_video(bc)
        bc.data['name'] = 'changed'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual('changed', video.title)
        lsc = zeit.cms.content.interfaces.ISemanticChange(video)
        self.assertEqual(
            datetime(2017, 5, 16, 8, 24, 55, 916000, tzinfo=pytz.UTC),
            lsc.last_semantic_change)

    def test_should_publish_after_update(self):
        bc = create_video()
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        last_published = info.date_last_published
        import_video(bc)
        self.assertGreater(info.date_last_published, last_published)

    def test_should_publish_only_once(self):
        # Safetybelt against the "publish videos after checkin" feature
        bc = create_video()
        import_video(bc)  # Create CMS object
        with mock.patch('zeit.workflow.publish.Publish.publish') as publish:
            import_video(bc)
            self.assertEqual(1, publish.call_count)

    def test_should_ignore_publish_for_already_locked_object(self):
        bc = create_video()
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        last_published = info.date_last_published

        zope.security.management.endInteraction()
        with zeit.cms.testing.interaction('zope.producer'):
            zeit.cms.checkout.interfaces.ICheckoutManager(video).checkout()
        zeit.cms.testing.create_interaction('zope.user')

        import_video(bc)
        self.assertEqual(info.date_last_published, last_published)

    def test_ignored_video_should_not_be_added_to_cms(self):
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/2017-05/myvid', None))
        bc = create_video()
        bc.data['custom_fields']['ignore_for_update'] = '1'
        import_video(bc)
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/2017-05/myvid', None))

    def test_ignored_video_should_not_be_updated_in_cms(self):
        bc = create_video()
        import_video(bc)
        bc.data['name'] = 'changed'
        bc.data['custom_fields']['ignore_for_update'] = '1'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual('title', video.title)

    def test_inactive_video_should_be_retracted(self):
        bc = create_video()
        import_video(bc)
        bc.data['state'] = 'INACTIVE'
        with mock.patch('zeit.workflow.publish.Publish.retract') as retract:
            import_video(bc)
            self.assertEqual(True, retract.called)

    def test_inactive_video_should_be_imported_but_not_published(self):
        bc = create_video()
        bc.data['state'] = 'INACTIVE'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        self.assertEqual(False, info.published)

    def test_changes_to_inactive_video_should_be_imported(self):
        bc = create_video()
        import_video(bc)
        bc.data['name'] = 'changed'
        bc.data['state'] = 'INACTIVE'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual('changed', video.title)
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        self.assertEqual(False, info.published)

    def test_deleted_video_should_be_deleted_from_cms(self):
        bc = create_video()
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        deleted = zeit.brightcove.convert.DeletedVideo(bc.id, video)
        import_video(deleted)
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/2017-05/myvid', None))

    def test_deleted_video_should_be_retracted(self):
        bc = create_video()
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        deleted = zeit.brightcove.convert.DeletedVideo(bc.id, video)
        with mock.patch('zeit.workflow.publish.Publish.retract') as retract:
            import_video(deleted)
            self.assertEqual(True, retract.called)

    def test_vanished_video_should_be_ignored(self):
        bc = create_video()
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        del video.__parent__[video.__name__]
        deleted = zeit.brightcove.convert.DeletedVideo(bc.id, None)
        with self.assertNothingRaised():
            import_video(deleted)

    def test_new_video_should_bbb_copy_authors(self):
        author = zeit.content.author.author.Author()
        author.firstname = u'William'
        author.lastname = u'Shakespeare'
        self.repository['author'] = author
        bc = create_video()
        bc.data['custom_fields']['authors'] = 'http://xml.zeit.de/author'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual(('William Shakespeare',), video.authors)

    def test_changed_video_should_bbb_copy_authors(self):
        author = zeit.content.author.author.Author()
        author.firstname = u'William'
        author.lastname = u'Shakespeare'
        self.repository['author'] = author
        bc = create_video()
        import_video(bc)
        bc.data['custom_fields']['authors'] = 'http://xml.zeit.de/author'
        import_video(bc)
        video = ICMSContent('http://xml.zeit.de/video/2017-05/myvid')
        self.assertEqual(('William Shakespeare',), video.authors)


class TestDownloadTeasers(zeit.brightcove.testing.StaticBrowserTestCase):

    def setUp(self):
        super(TestDownloadTeasers, self).setUp()
        image_dir = pkg_resources.resource_filename(
            "zeit.content.image.browser", "testdata"
        )
        shutil.copytree(image_dir, path.join(self.layer["documentroot"], "testdata"))

    def test_download_teaser_image__thumbnail_success(self):
        src = "http://{0.layer[http_address]}/testdata/opernball.jpg".format(self)
        bc = create_video()
        bc.data['images']['thumbnail']['src'] = src
        import_video(bc)
        # importing the video has created an image group "next to it" for its thumbnail
        # and has assigned it as its thumbnail
        assert self.repository['video']['2017-05']['myvid'].cms_thumbnail == self.repository['video']['2017-05']['myvid-thumbnail']
        # the video has been published
        self.assertEqual(
            True,
            zeit.cms.workflow.interfaces.IPublishInfo(
                ICMSContent('http://xml.zeit.de/video/2017-05/myvid')).published)
        # and so has the thumbnail
        self.assertEqual(
            True,
            zeit.cms.workflow.interfaces.IPublishInfo(
                ICMSContent('http://xml.zeit.de/video/2017-05/myvid-thumbnail')).published)

    def test_download_teaser_image__still_success(self):
        src = "http://{0.layer[http_address]}/testdata/opernball.jpg".format(self)
        bc = create_video()
        bc.data['images']['poster']['src'] = src
        import_video(bc)
        # importing the video has created an image group "next to it" for its still image
        assert self.repository['video']['2017-05']['myvid'].cms_video_still == self.repository['video']['2017-05']['myvid-still']
        self.assertEqual(
            True,
            zeit.cms.workflow.interfaces.IPublishInfo(
                ICMSContent('http://xml.zeit.de/video/2017-05/myvid-still')).published)

    def test_download_teaser_image_error_produces_empty_group(self):
        zeit.brightcove.update.download_teaser_image(
            self.repository,
            dict(
                id="foo",
                images=dict(
                    thumbnail=dict(src="foo"))),
            "thumbnail")
        group = self.repository['foo-thumbnail']
        assert group.master_image is None

    def test_download_teaser_for_locked_image_ignored(self):
        with mock.patch(
            'zeit.brightcove.convert.image_group_from_image'
        ) as patched:
            patched.side_effect = zope.app.locking.interfaces.LockingError()
            assert zeit.brightcove.update.download_teaser_image(
                self.repository,
                dict(
                    id="foo",
                    images=dict(
                        thumbnail=dict(src="foo"))),
                "thumbnail") is None

    def test_download_teaser_image_error_uses_existing(self):
        from zeit.content.image.testing import create_image_group_with_master_image
        self.repository['foo-thumbnail'] = create_image_group_with_master_image()
        existing = self.repository['foo-thumbnail']
        existing.stamped = 'this'
        new = zeit.brightcove.update.download_teaser_image(
            self.repository,
            dict(
                id="foo",
                images=dict(
                    thumbnail=dict(src="foo"))),
            "thumbnail")
        assert new.stamped == 'this'

    def test_update_teaser_image_still_success(self):
        src = "http://{0.layer[http_address]}/testdata/opernball.jpg".format(self)
        bc = create_video()
        bc.data['images']['poster']['src'] = src
        imported = import_video(bc)
        assert imported.cmsobj.cms_video_still.master_image == 'opernball.jpg'
        new_src = "http://{0.layer[http_address]}/testdata/obama-clinton-120x120.jpg".format(self)
        bc.data['images']['poster']['src'] = new_src
        # importing it again triggers update:
        reimported = import_video(bc)
        assert reimported.cmsobj.cms_video_still.master_image == 'obama-clinton-120x120.jpg'

    def test_update_teaser_image_preserves_override(self):
        from zeit.content.image.testing import create_image_group_with_master_image
        src = "http://{0.layer[http_address]}/testdata/opernball.jpg".format(self)
        # video is created via BC import
        bc = create_video()
        bc.data['images']['poster']['src'] = src
        import_video(bc)
        # editor replaces automatically created video still with custom imagegroup
        self.repository['foo-video_still'] = create_image_group_with_master_image()
        self.repository['video']['2017-05']['myvid'].cms_video_still = self.repository['foo-video_still']
        assert self.repository['video']['2017-05']['myvid'].cms_video_still.master_image == 'master-image.jpg'
        # now an update from brightcove still updates the automatically created image group:
        new_src = "http://{0.layer[http_address]}/testdata/obama-clinton-120x120.jpg".format(self)
        bc.data['images']['poster']['src'] = new_src
        reimported = import_video(bc)
        assert self.repository['video']['2017-05']['myvid-still'].master_image == 'obama-clinton-120x120.jpg'
        # but it does not change the reference of the video to the custom imagegroup
        assert reimported.cmsobj.cms_video_still.master_image == 'master-image.jpg'


class ImportPlaylistTest(zeit.brightcove.testing.FunctionalTestCase):

    def create_playlist(self):
        bc = zeit.brightcove.convert.Playlist()
        bc.data = {
            'id': 'mypls',
            'name': 'title',
            'updated_at': '2017-05-15T08:24:55.916Z',
        }
        return bc

    def test_new_playlist_should_be_added_to_cms(self):
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/playlist/mypls', None))
        import_playlist(self.create_playlist())
        playlist = ICMSContent('http://xml.zeit.de/video/playlist/mypls')
        self.assertEqual('title', playlist.title)
        info = zeit.cms.workflow.interfaces.IPublishInfo(playlist)
        self.assertEqual(True, info.published)

    def test_changed_playlist_should_be_written_to_cms_if_newer(self):
        bc = self.create_playlist()
        import_playlist(bc)
        playlist = ICMSContent('http://xml.zeit.de/video/playlist/mypls')
        self.assertEqual('title', playlist.title)
        info = zeit.cms.workflow.interfaces.IPublishInfo(playlist)
        last_published = info.date_last_published

        bc.data['name'] = 'changed'
        import_playlist(bc)
        playlist = ICMSContent('http://xml.zeit.de/video/playlist/mypls')
        self.assertEqual('title', playlist.title)

        bc.data['updated_at'] = '2017-05-16T08:24:55.916Z'
        import_playlist(bc)

        playlist = ICMSContent('http://xml.zeit.de/video/playlist/mypls')
        self.assertEqual('changed', playlist.title)
        lsc = zeit.cms.content.interfaces.ISemanticChange(playlist)
        self.assertEqual(
            datetime(2017, 5, 16, 8, 24, 55, 916000, tzinfo=pytz.UTC),
            lsc.last_semantic_change)
        self.assertGreater(info.date_last_published, last_published)

    def test_unknown_playlist_should_be_deleted(self):
        bc = self.create_playlist()
        import_playlist(bc)
        other = self.create_playlist()
        other.data['id'] = 'other'
        import_playlist(other)

        import_playlist.delete_except([other])
        self.assertEqual(
            None, ICMSContent('http://xml.zeit.de/video/playlist/mypls', None))
        self.assertNotEqual(
            None, ICMSContent('http://xml.zeit.de/video/playlist/other', None))


class ExportTest(zeit.brightcove.testing.FunctionalTestCase):

    def setUp(self):
        super(ExportTest, self).setUp()
        self.repository['myvid'] = zeit.content.video.video.Video()
        self.request_patch = mock.patch(
            'zeit.brightcove.connection.CMSAPI._request')
        self.request = self.request_patch.start()

    def tearDown(self):
        self.request_patch.stop()
        super(ExportTest, self).tearDown()

    def test_video_changes_are_written_to_brightcove_on_checkin(self):
        with zeit.cms.checkout.helper.checked_out(
                self.repository['myvid'], semantic_change=True) as co:
            co.title = u'local change'
        transaction.commit()
        self.assertEqual(1, self.request.call_count)
        self.assertEqual(
            'local change', self.request.call_args[1]['body']['name'])

    def test_changes_are_not_written_during_publish(self):
        zeit.cms.workflow.interfaces.IPublish(
            self.repository['myvid']).publish(background=False)
        self.assertEqual(False, self.request.called)

    def test_changes_are_written_on_commit(self):
        video = zeit.brightcove.convert.Video()
        zeit.brightcove.session.get().update_video(video)
        transaction.commit()
        self.assertEqual(1, self.request.call_count)
        # Changes are not written again
        transaction.commit()
        self.assertEqual(1, self.request.call_count)

    def test_changes_are_not_written_on_abort(self):
        video = zeit.brightcove.convert.Video()
        zeit.brightcove.session.get().update_video(video)
        transaction.abort()
        self.assertEqual(0, self.request.call_count)

    def test_video_is_published_on_checkin(self):
        video = self.repository['myvid']
        zeit.cms.workflow.interfaces.IPublish(video).publish(background=False)
        info = zeit.cms.workflow.interfaces.IPublishInfo(video)
        last_published = info.date_last_published

        with zeit.cms.checkout.helper.checked_out(video):
            pass
        transaction.commit()

        self.assertGreater(info.date_last_published, last_published)

    def test_playlist_is_published_on_checkin(self):
        self.repository['playlist'] = zeit.content.video.playlist.Playlist()
        playlist = self.repository['playlist']
        zeit.cms.workflow.interfaces.IPublish(playlist).publish(
            background=False)
        info = zeit.cms.workflow.interfaces.IPublishInfo(playlist)
        last_published = info.date_last_published

        with zeit.cms.checkout.helper.checked_out(playlist):
            pass
        transaction.commit()

        self.assertGreater(info.date_last_published, last_published)
