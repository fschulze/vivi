# Copyright (c) 2011 gocept gmbh & co. kg
# See also LICENSE.txt

from zeit.cms.i18n import MessageFactory as _
from zeit.cms.tagging.interfaces import KEYWORD_CONFIGURATION
from zeit.cms.tagging.tag import Tag
import grokcore.component
import json
import xml.sax.saxutils
import zc.resourcelibrary
import zeit.cms.browser.interfaces
import zeit.cms.browser.view
import zeit.cms.tagging.interfaces
import zope.app.pagetemplate
import zope.formlib.itemswidgets
import zope.formlib.source
import zope.formlib.widget
import zope.lifecycleevent
import zope.schema.interfaces


class Widget(grokcore.component.MultiAdapter,
             zope.formlib.widget.SimpleInputWidget):
    """Widget to edit tags on context.

    - "Update" link uses an tagging mechanism to add tags to content
    - The user can sort and (de-)activate tags, but not manually add them.

    """

    grokcore.component.adapts(
        zope.schema.interfaces.ITuple,
        zeit.cms.tagging.interfaces.ITagsForContent,
        zeit.cms.browser.interfaces.ICMSLayer)
    grokcore.component.provides(
        zope.formlib.interfaces.IInputWidget)

    template = zope.app.pagetemplate.ViewPageTemplateFile('widget.pt')

    show_helptext = False

    def __init__(self, context, source, request):
        super(Widget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        zc.resourcelibrary.need('zeit.cms.tagger')
        return self.template()

    @property
    def keywords_shown(self):
        return KEYWORD_CONFIGURATION.keywords_shown

    def _toFormValue(self, value):
        return json.dumps([{'code': x.code, 'label': x.label} for x in value])

    def _toFieldValue(self, value):
        tags = json.loads(value)
        return tuple(Tag(x['code'], x['label']) for x in tags)


class UpdateTags(zeit.cms.browser.view.JSON):

    def json(self):
        tagger = zeit.cms.tagging.interfaces.ITagger(self.context)
        tagger.update()
        zope.lifecycleevent.modified(self.context)
        return dict(tags=[
            dict(code=tag.code,
                 label=tag.label)
            for tag in tagger.values()])


class DisplayWidget(grokcore.component.MultiAdapter,
                    zope.formlib.itemswidgets.ListDisplayWidget):

    grokcore.component.adapts(
        zope.schema.interfaces.ITuple,
        zeit.cms.tagging.interfaces.ITagsForContent,
        zeit.cms.browser.interfaces.ICMSLayer)
    grokcore.component.provides(
        zope.formlib.interfaces.IDisplayWidget)

    def __init__(self, field, source, request):
        super(DisplayWidget, self).__init__(
            field,
            zope.formlib.source.IterableSourceVocabulary(source, request),
            request)

    def __call__(self):
        return zope.formlib.widget.renderElement(
            'div',
            cssClass='keyword-widget',
            contents=super(DisplayWidget, self).__call__(),
            id=self.name)

    def renderItems(self, value):
        """Render items of sequence."""
        # XXX blame formlib for having to copy this method
        items = []
        cssClass = self.cssClass or ''
        if cssClass:
            cssClass += "-item"
        cssClass += ' shown'
        tag = self.itemTag
        for index, item in enumerate(value):
            if index >= KEYWORD_CONFIGURATION.keywords_shown:
                continue
            term = self.vocabulary.getTerm(item)
            items.append(zope.formlib.widget.renderElement(
                tag,
                cssClass=cssClass,
                contents=xml.sax.saxutils.escape(self.textForValue(term))))
        return items
