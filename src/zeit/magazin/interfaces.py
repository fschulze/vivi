from zeit.cms.i18n import MessageFactory as _
import zc.form.field
import zeit.cms.interfaces
import zeit.cms.related.interfaces
import zeit.cms.section.interfaces
import zeit.content.article.interfaces
import zeit.content.cp.interfaces
import zeit.content.portraitbox.interfaces
import zeit.magazin.sources
import zope.interface
import zope.schema


class IZMOSection(zeit.cms.section.interfaces.ISection):
    pass


class IZMOContent(
        zeit.cms.interfaces.ICMSContent,
        zeit.cms.section.interfaces.ISectionMarker):
    pass


class IZMOFolder(
        zeit.cms.repository.interfaces.IFolder,
        zeit.cms.section.interfaces.ISectionMarker):
    pass


class IZMOArticle(
        zeit.content.article.interfaces.IArticle,
        zeit.cms.section.interfaces.ISectionMarker):
    pass


class IZMOCenterPage(
        zeit.content.cp.interfaces.ICenterPage,
        zeit.cms.section.interfaces.ISectionMarker):
    pass


class IZMOPortraitbox(
        zeit.content.portraitbox.interfaces.IPortraitbox,
        zeit.cms.section.interfaces.ISectionMarker):
    pass


class IArticleTemplateSettings(zope.interface.Interface):

    template = zope.schema.Choice(
        title=_("Template"),
        source=zeit.magazin.sources.ArticleTemplateSource(),
        required=False)

    header_layout = zope.schema.Choice(
        title=_("Header layout"),
        source=zeit.magazin.sources.ArticleHeaderSource(),
        required=False)


class INextRead(zope.interface.Interface):

    nextread = zope.schema.Tuple(
        title=_("Next read"),
        default=(),
        required=False,
        value_type=zope.schema.Choice(
            source=zeit.cms.related.interfaces.relatableContentSource))


class IRelatedLayout(zope.interface.Interface):

    related_layout = zope.schema.Choice(
        title=_("Related layout"),
        source=zeit.magazin.sources.ArticleRelatedLayoutSource(),
        required=False)

    nextread_layout = zope.schema.Choice(
        title=_("Next read layout"),
        source=zeit.magazin.sources.ArticleRelatedLayoutSource(),
        required=False)


class IPortraitboxLongtext(zope.interface.Interface):

    longtext = zc.form.field.HTMLSnippet(
        title=_("long text (ZMO)"),
        required=False)
