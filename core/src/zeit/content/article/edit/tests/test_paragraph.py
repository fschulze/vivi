# Copyright (c) 2010 gocept gmbh & co. kg
# See also LICENSE.txt

import unittest
import zeit.content.article.testing


class ParagraphTest(unittest.TestCase):

    def get_paragraph(self, p=''):
        from zeit.content.article.edit.paragraph import Paragraph
        import lxml.objectify
        body = lxml.objectify.E.body(lxml.objectify.XML('<p>%s</p>' % p))
        return Paragraph(None, body.p)

    def test_setting_text_inserts_xml(self):
        p = self.get_paragraph()
        self.assertEquals(u'', p.text)
        text =  u'The quick brown fox jumps over the lazy dog.'
        p.text = text
        self.assertEqual(text, p.text)
        text =  u'The quick brown <em>fox</em> jumps over the lazy dog.'
        p.text = text
        self.assertEqual(text, p.text)

    def test_node_tails_should_be_include_in_text(self):
        p = self.get_paragraph('Im <strong>Tal</strong> der Buchstaben')
        self.assertEqual(u'Im <strong>Tal</strong> der Buchstaben', p.text)

    def test_setting_invalid_xml_is_somehow_converted_to_valid_xml(self):
        p = self.get_paragraph()
        p.text = u'<em>4 > 3'
        self.assertEqual('<em>4 &gt; 3</em>', p.text)

    def test_setting_text_should_keep_attributes(self):
        p = self.get_paragraph()
        p.xml.set('myattr', 'avalue')
        p.text = 'Mary had a little lamb.'
        self.assertEqual('avalue', p.xml.get('myattr'))

    def test_setting_unicode_should_work(self):
        p = self.get_paragraph()
        p.text = u'F\xfc!'
        self.assertEqual(u'F\xfc!', p.text)
        self.assertTrue(isinstance(p.text, unicode))

    def test_text_should_be_unicode(self):
        p = self.get_paragraph()
        p.text = 'Dadudeldum'
        self.assertTrue(isinstance(p.text, unicode))

    def test_setting_html_should_create_proper_xml(self):
        import lxml.objectify
        p = self.get_paragraph()
        p.text = u'I am <strong>strong</strong><br>I am the best.'
        self.assertEqual(u'I am <strong>strong</strong><br/>I am the best.',
                         p.text)
        self.assertTrue(isinstance(p.xml, lxml.objectify.ObjectifiedElement),
                        type(p.xml))

    def test_setting_html_with_block_elements_should_keep_p_as_xml_tag(self):
        p = self.get_paragraph()
        p.text = u'<h3>I am </h3><p>I am the best.</p>'
        self.assertEqual(p.type, p.xml.tag)

    def test_simple_text_should_be_escaped_correctly(self):
        p = self.get_paragraph()
        p.text = u'a > b'
        self.assertEqual('a &gt; b', p.text)

    def test_b_should_be_replaced_by_strong(self):
        p = self.get_paragraph()
        p.text = u'I am <b>strong</b>.'
        self.assertEqual('I am <strong>strong</strong>.', p.text)

    def test_i_should_be_replaced_by_em(self):
        p = self.get_paragraph()
        p.text = u'I am <i>strong</i>.'
        self.assertEqual('I am <em>strong</em>.', p.text)

    def test_u_should_be_allowed(self):
        p = self.get_paragraph()
        p.text = u'I am <u>underlined</u>.'
        self.assertEqual('I am <u>underlined</u>.', p.text)

    def test_br_should_be_allowed(self):
        p = self.get_paragraph()
        p.text = u'I am <br/>here and<br/>here.'
        self.assertEqual('I am <br/>here and<br/>here.', p.text)

    def test_a_witout_href_should_be_escaped(self):
        p = self.get_paragraph()
        p.text = u'A stupid <a>link</a>.'
        self.assertEqual(u'A stupid &lt;a&gt;link.', p.text)

    def test_a_with_href_should_be_allowed(self):
        p = self.get_paragraph()
        p.text = u'A working <a href="#">link'
        self.assertEqual(u'A working <a href="#">link</a>', p.text)

    def test_a_target_should_be_allowed(self):
        p = self.get_paragraph()
        p.text = u'A working <a href="#" target="_blank">link'
        self.assertEqual(u'A working <a href="#" target="_blank">link</a>',
                         p.text)


class UnorderedListTest(ParagraphTest):

    def get_paragraph(self, p=''):
        from zeit.content.article.edit.paragraph import UnorderedList
        import lxml.objectify
        body = lxml.objectify.E.body(lxml.objectify.XML('<ul>%s</ul>' % p))
        return UnorderedList(None, body.ul)


class OrderedListTest(ParagraphTest):

    def get_paragraph(self, p=''):
        from zeit.content.article.edit.paragraph import UnorderedList
        import lxml.objectify
        body = lxml.objectify.E.body(lxml.objectify.XML('<ol>%s</ol>' % p))
        return UnorderedList(None, body.ol)


class IntertitleTest(ParagraphTest):

    def get_paragraph(self, p=''):
        from zeit.content.article.edit.paragraph import UnorderedList
        import lxml.objectify
        body = lxml.objectify.E.body(lxml.objectify.XML(
            '<intertitle>%s</intertitle>' % p))
        return UnorderedList(None, body.intertitle)


class TestFactories(zeit.content.article.testing.FunctionalTestCase):

    def assert_factory(self, name):
        import zeit.content.article.article
        import zeit.content.article.edit.interfaces
        import zeit.edit.interfaces
        import zope.component
        article = zeit.content.article.article.Article()
        body = zeit.content.article.edit.body.EditableBody(
            article, article.xml.body)
        factory = zope.component.getAdapter(
            body, zeit.edit.interfaces.IElementFactory, name)
        self.assertEqual('<%s>' % name, factory.title)
        block = factory()
        self.assertTrue(
            zeit.content.article.edit.interfaces.IParagraph.providedBy(block))
        self.assertEqual(name, block.xml.tag)
        self.assertEqual('division', block.xml.getparent().tag)
        return block

    def test_p(self):
        self.assert_factory('p')

    def test_ul(self):
        self.assert_factory('ul')

    def test_ol(self):
        self.assert_factory('ol')

    def test_intertitle(self):
        self.assert_factory('intertitle')
