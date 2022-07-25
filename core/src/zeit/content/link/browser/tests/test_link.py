import lxml.etree
import zeit.content.link.link
import zeit.content.link.testing
import zope.app.appsetup


class TestForm(zeit.content.link.testing.BrowserTestCase):

    def create_link_object(self):
        link = zeit.content.link.link.Link()
        link.ressort = 'Politik'
        link.teaserTitle = 'gocept homepage'
        link.url = 'http://gocept.com'
        self.repository['online']['2007']['01']['gocept.link'] = link

    def test_adding_link_stores_values(self):
        b = self.browser
        b.open('http://localhost/++skin++vivi/repository/2006/')
        menu = b.getControl(name='add_menu')
        menu.displayValue = ['Link']
        b.open(menu.value[0])
        b.getControl('File name').value = 'gocept.link'
        b.getControl(name='form.teaserTitle').value = 'gocept homepage'
        b.getControl('Ressort', index=0).displayValue = ['Leben']
        b.getControl('Link address').value = 'http://gocept.com'
        b.getControl('HTTP Status Code').displayValue = ['307']
        b.getControl(name="form.image").value = \
            'http://xml.zeit.de/2006/DSC00109_2.JPG'
        b.getControl(name='form.actions.add').click()
        self.assertFalse('There were errors' in b.contents)
        b.getLink('Source').click()
        xml = b.getControl(name='form.xml').value
        self.assertTrue('<title>gocept homepage' in xml)
        self.assertTrue('<url>http://gocept.com' in xml)
        self.assertTrue('<status>307' in xml)
        self.assertEllipsis("""
        <link...
        <head>...
            <image...src="http://xml.zeit.de/2006/DSC00109_2.JPG"...>
            ...
            </image>...
         """, xml)
        self.assertTrue('name="ressort">Leben</attribute'
                        in xml)
        b.getLink('Checkin').click()
        self.assertFalse('There were errors' in b.contents)
        self.assertTrue('/2006/gocept.link' in b.url)

    def test_syndicate_link_object(self):
        self.create_link_object()
        b = self.browser
        b.open('http://localhost/++skin++cms/repository/politik.feed')
        b.getLink('Remember as syndication target').click()
        b.open('http://localhost/repository/online/2007/01/gocept.link')
        b.getLink('Syndicate').click()
        checkbox = b.getControl(
            name='selection_column'
                 '.aHR0cDovL3htbC56ZWl0LmRlL3BvbGl0aWsuZmVlZA==.')
        checkbox.value = True
        b.getControl('Syndicate').click()
        b.open('http://localhost/++skin++cms/repository/politik.feed')
        b.getLink('Checkout').click()
        b.getLink('Source').click()
        xml = b.getControl(name='form.xml').value
        block = lxml.etree.fromstring(xml).xpath('//block')[0]
        self.assertEqual('http://gocept.com',
                         block.get('{http://namespaces.zeit.de/CMS/link}href'))
        self.assertEqual('http://xml.zeit.de/online/2007/01/gocept.link',
                         block.get('href'))
        self.assertEqual('Politik',
                         block.get('ressort'))
        self.assertEqual('gocept homepage',
                         block.find('title').text)

    def test_checks_for_invalid_hostnames(self):
        config = zope.app.appsetup.product.getProductConfiguration('zeit.cms')
        config['invalid-link-targets'] = 'example.com other.com'
        b = self.browser
        b.open('http://localhost/++skin++vivi/repository/2006/')
        menu = b.getControl(name='add_menu')
        menu.displayValue = ['Link']
        b.open(menu.value[0])
        b.getControl('File name').value = 'mylink'
        b.getControl('Link address').value = 'http://example.com/test'
        b.getControl(name='form.actions.add').click()
        self.assertEllipsis('...Invalid link target...', b.contents)
