from collections import namedtuple
import json
import grokcore.component as grok
import zeit.cms.browser.interfaces
import zeit.cms.browser.view
import zeit.cms.interfaces
import zeit.cms.recipe.interfaces
import zope.app.appsetup.appsetup
import zope.app.pagetemplate
import zope.component.hooks
import zope.formlib.itemswidgets
import zope.formlib.source
import zope.formlib.widget
import zope.lifecycleevent
import zope.schema.interfaces
from zeit.content.article.edit.recipelist import Ingredient


class Widget(grok.MultiAdapter,
             zope.formlib.widget.SimpleInputWidget,
             zeit.cms.browser.view.Base):
    """Widget to edit recipes on context.

    """

    grok.adapts(
        zope.schema.interfaces.ITuple,
        zeit.cms.recipe.interfaces.IIngredientsSource,
        zeit.cms.browser.interfaces.ICMSLayer)
    grok.provides(zope.formlib.interfaces.IInputWidget)

    template = zope.app.pagetemplate.ViewPageTemplateFile('widget.pt')

    def __init__(self, context, source, request):
        __import__("pdb").set_trace()
        super(Widget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        return self.template()

    @property
    def autocomplete_source_url(self):
        return self.url(
            zope.component.hooks.getSite(), '@@find_ingredients')

    @property
    def uuid(self):
        return zeit.cms.content.interfaces.IUUID(self.context.context).id

    def _toFormValue(self, value):
        return json.dumps([{
            'id': x.id,
            'amount': x.amount} for x in value or ()])

    def _toFieldValue(self, value):
        data = json.loads(value)
        return tuple([Ingredient(x['id'], x['amount'] for x in data))


class DisplayWidget(grok.MultiAdapter,
                    zope.formlib.itemswidgets.ItemsWidgetBase):

    grok.adapts(
        zope.schema.interfaces.ITuple,
        zeit.cms.recipe.interfaces.IIngredientsSource,
        zeit.cms.browser.interfaces.ICMSLayer)
    grok.provides(zope.formlib.interfaces.IDisplayWidget)

    template = zope.app.pagetemplate.ViewPageTemplateFile('display-recipe.pt')
    # recipe_highling_css_class = 'with-topic-page'

    def __init__(self, field, source, request):
        __import__("pdb").set_trace()
        super(DisplayWidget, self).__init__(
            field,
            zope.formlib.source.IterableSourceVocabulary(source, request),
            request)
        tagger = zeit.cms.tagging.interfaces.ITagger(self.context.context)
        try:
            self.tags_with_topicpages = tagger.links
        except Exception:
            self.tags_with_topicpages = {}

    def __call__(self):
        return self.template()

    def _text(self, item):
        return self.textForValue(self.vocabulary.getTerm(item))

    def items(self):
        items = []
        Tag = namedtuple('Tag', ['text', 'link', 'css_class'])
        for item in self._getFormValue():
            text = self._text(item)
            link = self.tags_with_topicpages.get(item.uniqueId)
            css_class = self.tag_highling_css_class if link else ''
            items.append(Tag(text, link, css_class))
        return items
