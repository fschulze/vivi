from lxml.objectify import E
from zeit.cms.interfaces import CONFIG_CACHE
import collections
import gocept.lxml.objectify
import grokcore.component as grok
import logging
import lxml.etree
import six
import zeit.cms.browser.interfaces
import zeit.cms.browser.view
import zeit.wochenmarkt.interfaces
import zope.component
import zope.component.hooks


log = logging.getLogger(__name__)


def xpath_lowercase(context, x):
    return x[0].lower()


xpath_functions = lxml.etree.FunctionNamespace('zeit.categories')
xpath_functions['lower'] = xpath_lowercase


@grok.implementer(zeit.wochenmarkt.interfaces.IRecipeCategory)
class RecipeCategory(object):

    def __init__(self, code, name):
        self.code = code
        self.label = name
        self.__name__ = self.code

    @classmethod
    def from_xml(cls, node):
        return cls(node.get('code'), node.get('label'))


class RecipeCategories(object):
    """Property which stores recipe categories in DAV."""

    def __get__(self, instance, class_):
        return [RecipeCategory.from_xml(x) for x in (
                instance.xml.xpath('./recipe_categories/category'))]

    def __set__(self, instance, value):
        for node in instance.xml.xpath('./recipe_categories'):
            node.getparent().remove(node)
        value = self._remove_duplicates(value)
        el = E.recipe_categories()
        for item in value:
            el.append(
                E.category(
                    code=item.code,
                    label=item.label))
        instance.xml.append(el)

    def _remove_duplicates(self, ingredients):
        result = collections.OrderedDict()
        for ingredient in ingredients:
            if ingredient.code not in result:
                result[ingredient.code] = ingredient
        return result.values()


@grok.implementer(zeit.wochenmarkt.interfaces.IRecipeCategoriesWhitelist)
class RecipeCategoriesWhitelist(grok.GlobalUtility):
    """Search for categories in categories source"""

    @property
    def data(self):
        return self._load()

    def search(self, term):
        xml = self._fetch()
        nodes = xml.xpath(
            '//category[contains(zeit:lower(text()), "%s")]' %
            term.lower(), namespaces={'zeit': 'zeit.categories'})
        return [self.get(x.get('id')) for x in nodes]

    def get(self, code):
        result = self.data.get(code)
        return result if result else None

    @CONFIG_CACHE.cache_on_arguments()
    def _fetch(self):
        ns = 'zeit.wochenmarkt'
        config = zope.app.appsetup.product.getProductConfiguration(ns)
        url = config.get('categories-url')
        log.info('Loading categories from %s', url)
        data = six.moves.urllib.request.urlopen(url)
        return gocept.lxml.objectify.fromfile(data)

    @CONFIG_CACHE.cache_on_arguments()
    def _load(self):
        xml = self._fetch()
        categories = collections.OrderedDict()
        for category_node in xml.xpath('//category'):
            category = RecipeCategory(
                category_node.get('id'),
                six.text_type(category_node).strip())
            categories[category_node.get('id')] = category
        log.info('categories loaded.')
        return categories
