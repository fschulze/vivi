# coding: utf8
import zeit.cms.interfaces
import zeit.retresco.testing


class TagTest(zeit.retresco.testing.FunctionalTestCase):
    """Testing ..tag.Tag."""

    def test_from_code_generates_a_tag_object_equal_to_its_source(self):
        from ..tag import Tag
        tag = Tag(u'Vipraschül', 'Person')
        self.assertEqual(tag, Tag.from_code(tag.code))

    def test_uniqueId_from_tag_can_be_adapted_to_tag(self):
        from ..tag import Tag
        tag = Tag(u'Vipraschül', 'Person')
        self.assertEqual(tag, zeit.cms.interfaces.ICMSContent(tag.uniqueId))

    def test_comparison_to_object_that_is_no_tag_returns_False(self):
        from ..tag import Tag
        tag = Tag(u'Vipraschül', 'Person')
        self.assertEqual(False, tag == {})

    def test_not_equal_comparison_is_supported(self):
        from ..tag import Tag
        tag = Tag(u'Vipraschül', 'Person')
        self.assertEqual(False, tag != Tag(u'Vipraschül', 'Person'))
        self.assertEqual(True, tag != {})

    def test_from_code_returns_None_if_invalid_code_given(self):
        from ..tag import Tag
        self.assertEqual(None, Tag.from_code(u'invalid-code'))
