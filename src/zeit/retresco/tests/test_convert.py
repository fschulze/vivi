# coding: utf-8
from zeit.cms.checkout.helper import checked_out
from zeit.retresco.testing import create_testcontent
import datetime
import gocept.testing.assertion
import mock
import pytz
import zeit.cms.content.interfaces
import zeit.cms.content.sources
import zeit.cms.interfaces
import zeit.cms.tagging.testing
import zeit.content.image.interfaces
import zeit.content.volume.volume
import zeit.retresco.interfaces
import zeit.retresco.tag
import zeit.retresco.testing
import zope.interface
import zope.xmlpickle


class ConvertTest(zeit.retresco.testing.FunctionalTestCase,
                  gocept.testing.assertion.String):

    maxDiff = None

    def test_smoke_converts_lots_of_fields(self):
        article = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/Somalia')
        with checked_out(article) as co:
            co.breaking_news = True
            co.product = zeit.cms.content.sources.Product(u'KINZ')
            co.keywords = (
                zeit.retresco.tag.Tag('Code1', 'keyword'),
                zeit.retresco.tag.Tag('Code2', 'keyword'))
        article = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/Somalia')

        images = zeit.content.image.interfaces.IImages(article)
        image = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/2006/DSC00109_2.JPG')
        with checked_out(image) as co:
            zeit.content.image.interfaces.IImageMetadata(
                co).expires = datetime.datetime(2007, 4, 1)
        images.image = zeit.cms.interfaces.ICMSContent(image.uniqueId)

        data = zeit.retresco.interfaces.ITMSRepresentation(article)()

        # Extract fields for which we cannot easily/sensibly use assertEqual().
        self.assertStartsWith('{urn:uuid:', data.pop('doc_id'))
        self.assertStartsWith(
            '{urn:uuid:', data['payload']['document'].pop('uuid'))
        self.assertStartsWith(
            str(datetime.date.today().year),
            data['payload']['document'].pop('date_last_checkout'))
        self.assertStartsWith(
            str(datetime.date.today().year),
            data['payload']['document'].pop('date-last-modified'))
        self.assertStartsWith(
            '<pickle', data['payload']['meta'].pop('provides'))
        self.assertStartsWith(
            '<ns0:rankedTags', data['payload']['tagging'].pop('keywords'))
        self.assertStartsWith('<body', data.pop('body'))

        teaser = (
            u'Im Zuge des äthiopischen Vormarsches auf Mogadischu kriechen '
            u'in Somalia auch die alten Miliz-Chefs wieder hervor.')
        self.assertEqual({
            'author': u'Hans Meiser',
            'date': '1970-01-01T00:00:00Z',
            'doc_type': 'article',
            'payload': {
                'body': {
                    'byline': u'Von Jochen Stahnke',
                    'subtitle': teaser,
                    'supertitle': u'Somalia',
                    'title': u'Rückkehr der Warlords'
                },
                'document': {
                    'DailyNL': False,
                    'artbox_thema': False,
                    'author': ['Hans Meiser'],
                    'banner': True,
                    'banner_content': True,
                    'breaking_news': True,
                    'color_scheme': u'Redaktion',
                    'comments': False,
                    'comments_premoderate': False,
                    'copyrights': 'ZEIT online',
                    'countings': True,
                    'foldable': True,
                    'has_recensions': False,
                    'header_layout': u'default',
                    'hide_ligatus_recommendations': False,
                    'imagecount': '0',
                    'in_rankings': 'yes',
                    'is_amp': False,
                    'is_content': 'yes',
                    'is_instant_article': False,
                    'last_modified_by': u'zope.user',
                    'lead_candidate': True,
                    'minimal_header': False,
                    'mostread': 'yes',
                    'new_comments': '1',
                    'overscrolling': True,
                    'pagelabel': 'Online',
                    'paragraphsperpage': '6',
                    'rebrush_website_content': False,
                    'ressort': u'International',
                    'revision': '11',
                    'serie': u'-',
                    'show_commentthread': False,
                    'supertitle': 'Spitzmarke hierher',
                    'template': u'article',
                    'text-length': 1036,
                    'title': u'R\xfcckkehr der Warlords',
                    'tldr_milestone': False,
                    'topic': 'Politik',
                    'volume': 1,
                    'year': 2007
                },
                'head': {
                    'authors': [],
                    'teaser_image': u'http://xml.zeit.de/2006/DSC00109_2.JPG',
                },
                'meta': {
                    'type': 'article',
                },
                'tagging': {},
                'teaser': {
                    'text': teaser,
                    'title': u'Rückkehr der Warlords'
                },
                'vivi': {
                    'cms_icon': '/@@/zeit-content-article-interfaces-IArticle'
                                '-zmi_icon.png',
                    'cms_preview_url': '',
                    'publish_status': 'not-published'
                },
                'workflow': {
                    'last-modified-by': 'hegenscheidt',
                    'product-id': u'KINZ',
                    'status': u'OK'
                }
            },
            'rtr_events': [],
            'rtr_keywords': ['Code1', 'Code2'],
            'rtr_locations': [],
            'rtr_organisations': [],
            'rtr_persons': [],
            'rtr_products': [],
            'section': u'/International',
            'supertitle': u'Somalia',
            'teaser': teaser,
            'teaser_img_subline': None,
            'teaser_img_url': u'/2006/DSC00109_2.JPG',
            'title': u'Rückkehr der Warlords',
            'url': u'/online/2007/01/Somalia'
        }, data)

    def test_converts_channels_correctly(self):
        content = create_testcontent()
        content.channels = (('Mainchannel', None),)
        data = zeit.retresco.interfaces.ITMSRepresentation(content)()
        self.assertEqual(
            ['Mainchannel'], data['payload']['document']['channels'])

    def test_converts_storystreams_correctly(self):
        content = create_testcontent()
        source = zeit.cms.content.interfaces.ICommonMetadata[
            'storystreams'].value_type.source(None)
        content.storystreams = (source.find('test'),)
        data = zeit.retresco.interfaces.ITMSRepresentation(content)()
        self.assertEqual(['test'],
                         data['payload']['document']['storystreams'])

    def test_synthesizes_tms_teaser_if_none_present(self):
        content = create_testcontent()
        content.teaserText = None
        data = zeit.retresco.interfaces.ITMSRepresentation(content)()
        self.assertEqual('title', data['teaser'])

    def test_converts_volumes(self):
        volume = zeit.content.volume.volume.Volume()
        volume.uniqueId = 'http://xml.zeit.de/volume'
        zeit.cms.content.interfaces.IUUID(volume).id = 'myid'
        volume.year = 2015
        volume.volume = 1
        published = datetime.datetime(2015, 1, 1, 0, 0, tzinfo=pytz.UTC)
        volume.date_digital_published = published
        data = zeit.retresco.interfaces.ITMSRepresentation(volume)()
        self.assertEqual(u'Teäser 01/2015', data['title'])
        self.assertEqual(u'Teäser 01/2015', data['teaser'])
        self.assertEqual(
            published.isoformat(),
            data['payload']['document']['date_digital_published'])

    def test_does_not_index_volume_properties_for_articles(self):
        content = create_testcontent()
        content.year = 2006
        content.volume = 49
        content_teaser = 'content teaser'
        content.teaserText = content_teaser
        content.product = zeit.cms.content.sources.Product(u'ZEI')
        self.repository['content'] = content
        volume = zeit.content.volume.volume.Volume()
        volume.year = content.year
        volume.volume = content.volume
        volume.product = zeit.cms.content.sources.Product(u'ZEI')
        self.repository['2006']['49']['ausgabe'] = volume

        found = zeit.content.volume.interfaces.IVolume(content)
        self.assertEqual(found, volume)

        data = zeit.retresco.interfaces.ITMSRepresentation(content)()
        self.assertEqual(content_teaser, data['teaser'])

    def test_drops_empty_properties(self):
        content = create_testcontent()
        props = zeit.connector.interfaces.IWebDAVProperties(content)
        props[('page', 'http://namespaces.zeit.de/CMS/document')] = None
        props[('reported_on', 'http://namespaces.zeit.de/CMS/vgwort')] = ''
        data = zeit.retresco.interfaces.ITMSRepresentation(content)()
        self.assertNotIn('page', data['payload']['document'])
        self.assertNotIn('vgwort', data['payload'])
