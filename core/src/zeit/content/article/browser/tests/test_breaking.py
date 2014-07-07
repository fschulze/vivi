from zeit.cms.interfaces import ICMSContent
from zeit.cms.testcontenttype.testcontenttype import TestContentType
from zeit.cms.workflow.interfaces import IPublishInfo, IPublish
from zeit.content.article.edit.interfaces import IEditableBody
import lxml.etree
import zeit.cms.checkout.helper
import zeit.cms.testing
import zeit.content.article.interfaces
import zeit.content.article.testing
import zeit.workflow.testing
import zope.i18n.translationdomain


class TestAdding(zeit.cms.testing.BrowserTestCase):

    layer = zeit.content.article.testing.LAYER

    def setUp(self):
        super(TestAdding, self).setUp()
        domain = zope.i18n.translationdomain.TranslationDomain('zeit.cms')
        self.zca.patch_utility(domain, name='zeit.cms')
        self.catalog = zeit.cms.testing.TestCatalog()
        domain.addCatalog(self.catalog)

        for name, notifier in zope.component.getUtilitiesFor(
                zeit.push.interfaces.IPushNotifier):
            notifier.reset()

        self.browser.open(
            'http://localhost:8080/++skin++vivi/repository/online/2007/01/')

    def create_breakingnews(self):
        b = self.browser
        menu = b.getControl(name='add_menu')
        menu.displayValue = ['Add breaking news']
        b.open(menu.value[0])

    def fill_in_required_values(self):
        b = self.browser
        b.getControl('Ressort').displayValue = ['International']
        b.getControl('Title').value = 'Mytitle'
        b.getControl('File name').value = 'foo'

    def test_default_values_should_be_set(self):
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Publish and push').click()
        with zeit.cms.testing.site(self.getRootFolder()):
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            # XXX Kind of duplicate from .test_form.TestAdding
            self.assertEqual(2008, article.year)
            self.assertEqual(26, article.volume)
            self.assertEqual('ZEDE', article.product.id)
            self.assertEqual(True, article.commentsAllowed)

    def test_marks_article_as_breaking(self):
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Publish and push').click()
        with zeit.cms.testing.site(self.getRootFolder()):
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            self.assertEqual(
                True, zeit.content.article.interfaces.IBreakingNews(
                    article).is_breaking)
            self.assertEllipsis(
                '...<attribute...name="is_breaking">yes</attribute>...',
                lxml.etree.tostring(article.xml, pretty_print=True))

    def test_publish_sends_push_messages(self):
        # This tests the integration with zeit.push, but not the actual push
        # methods themselves.
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Publish and push').click()
        self.browser.open('@@publish')

        with zeit.cms.testing.site(self.getRootFolder()):
            with zeit.cms.testing.interaction():
                zeit.workflow.testing.run_publish()
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            self.assertEqual(True, IPublishInfo(article).published)
            for service in ['homepage', 'ios-legacy', 'wrapper', 'parse',
                            'twitter']:
                # XXX temporarily disabled Facebook
                #             'twitter', 'facebook']:
                notifier = zope.component.getUtility(
                    zeit.push.interfaces.IPushNotifier, name=service)
                self.assertEqual(1, len(notifier.calls))
                self.assertEqual(article.title, notifier.calls[0][0])

            parse = zope.component.getUtility(
                zeit.push.interfaces.IPushNotifier, name='parse')
            self.assertEqual('Eilmeldung', parse.calls[0][2]['title'])
            # XXX temporarily disabled Facebook
            # facebook = zope.component.getUtility(
            #     zeit.push.interfaces.IPushNotifier, name='facebook')
            # self.assertEqual(
            #     zeit.push.facebook.facebookAccountSource(None).MAIN_ACCOUNT,
            #     facebook.calls[0][2]['account'])

    def test_banners_and_parse_are_disabled_after_publish(self):
        # The breaking news is a normal article, so it has the normal social
        # media functionality, thus it may be "armed" again later on
        # (IPushMessages.enabled). But that should of course only apply to
        # those push services actually meant by the social media UI (i.e.
        # Twitter+Facebook), and not send "breaking news" messages again
        # (e.g. to mobile devices).
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Publish and push').click()
        self.browser.open('@@publish')

        with zeit.cms.testing.site(self.getRootFolder()):
            with zeit.cms.testing.interaction():
                zeit.workflow.testing.run_publish()
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            push = zeit.push.interfaces.IPushMessages(article)
            self.assertIn(
                {'type': 'parse', 'enabled': False, 'title': 'Eilmeldung'},
                push.message_config)
            self.assertIn(
                {'type': 'homepage', 'enabled': False}, push.message_config)
            self.assertIn(
                {'type': 'ios-legacy', 'enabled': False}, push.message_config)
            self.assertIn(
                {'type': 'wrapper', 'enabled': False}, push.message_config)

    def test_setting_body_text_creates_paragraph(self):
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Article body').value = 'mytext'
        self.browser.getControl('Publish and push').click()

        with zeit.cms.testing.site(self.getRootFolder()):
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            body = IEditableBody(article)
            para = body.values()[1]  # 0 is image
            self.assertEqual('mytext', para.text)

    def test_body_text_not_given_creates_no_paragraph(self):
        self.create_breakingnews()
        self.fill_in_required_values()
        self.browser.getControl('Article body').value = ''
        self.browser.getControl('Publish and push').click()

        with zeit.cms.testing.site(self.getRootFolder()):
            article = ICMSContent('http://xml.zeit.de/online/2007/01/foo')
            body = IEditableBody(article)
            self.assertEqual(1, len(body))

    def test_body_text_default_value_is_translated(self):
        b = self.browser
        b.addHeader('Accept-Language', 'tt')
        self.catalog.messages['breaking-news-more-shortly'] = 'foo'
        self.create_breakingnews()
        self.assertEqual('foo', b.getControl('Article body').value)


class RetractBannerTest(
        zeit.content.article.testing.SeleniumTestCase,
        zeit.workflow.testing.RemoteTaskHelper):

    def setUp(self):
        super(RetractBannerTest, self).setUp()
        with zeit.cms.testing.site(self.getRootFolder()):
            # Set up dummy banner articles.
            for name in ['homepage', 'ios-legacy', 'wrapper']:
                content = TestContentType()
                self.repository[name] = content
                notifier = zope.component.getUtility(
                    zeit.push.interfaces.IPushNotifier, name=name)
                notifier.uniqueId = content.uniqueId

            # Publish homepage banner so the retract button is shown.
            with zeit.cms.testing.interaction():
                IPublishInfo(self.repository['homepage']).urgent = True
                IPublish(self.repository['homepage']).publish()
                zeit.workflow.testing.run_publish()

            # Make Somalia breaking news, so the retract section is shown.
            article = ICMSContent(
                'http://xml.zeit.de/online/2007/01/Somalia')
            with zeit.cms.testing.interaction():
                with zeit.cms.checkout.helper.checked_out(article) as co:
                    zeit.content.article.interfaces.IBreakingNews(
                        co).is_breaking = True

        self.start_tasks()

    def tearDown(self):
        self.stop_tasks()
        for name in ['homepage', 'ios-legacy', 'wrapper']:
            notifier = zope.component.getUtility(
                zeit.push.interfaces.IPushNotifier, name=name)
            del notifier.uniqueId
        super(RetractBannerTest, self).tearDown()

    def test_retract_banner_endtoend(self):
        self.open('/repository/online/2007/01/Somalia')
        s = self.selenium
        s.waitForElementPresent('id=breaking-retract')
        s.assertElementPresent(
            'css=#breaking-retract .publish-state.published')
        s.click('id=breaking-retract-banner')
        s.waitForElementPresent('css=.lightbox')
        # Retract happens...
        s.waitForElementNotPresent('css=.lightbox')
        # Button is gone now, since there's nothing to retract anymore
        s.waitForElementNotPresent('id=breaking-retract-banner')
        s.assertElementPresent(
            'css=#breaking-retract .publish-state.not-published')
