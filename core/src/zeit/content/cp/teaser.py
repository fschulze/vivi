# Copyright (c) 2009 gocept gmbh & co. kg
# See also LICENSE.txt

from zeit.content.cp.i18n import MessageFactory as _
import lxml.etree
import lxml.objectify
import rwproperty
import zeit.cms.content.property
import zeit.cms.repository.interfaces
import zeit.cms.syndication.feed
import zeit.cms.syndication.interfaces
import zeit.content.cp.block
import zeit.content.cp.interfaces
import zope.component
import zope.container.interfaces
import zope.interface
import zope.schema


class TeaserList(zeit.content.cp.block.Block,
                 zeit.cms.syndication.feed.Feed):

    # TeaserList reuses Feed for its "list of ICMSContent" behaviour

    zope.interface.implementsOnly(
        zeit.content.cp.interfaces.ITeaserList,
        zeit.cms.syndication.interfaces.IFeed,
        zope.container.interfaces.IContained)

    # XXX XSLT must drop these
    _autopilot = zeit.cms.content.property.ObjectPathProperty('.autopilot')
    referenced_cp = zeit.cms.content.property.SingleResource('.referenced_cp')

    @property
    def entries(self):
        # overriden so that super.insert() and updateOrder() work
        return self.xml

    def iterentries(self):
        if self.autopilot:
            repository = zope.component.getUtility(
                zeit.cms.repository.interfaces.IRepository)
            return [repository.getContent(id) for id in self.keys()]
        else:
            return super(TeaserList, self).iterentries()

    def keys(self):
        if self.autopilot:
            return zeit.content.cp.interfaces.ILeadTeasers(self.referenced_cp)
        else:
            return super(TeaserList, self).keys()

    def insert(self, *args, **kw):
        self._forbidden_on_autopilot('insert', *args, **kw)

    def remove(self, *args, **kw):
        self._forbidden_on_autopilot('remove', *args, **kw)

    def updateOrder(self, *args, **kw):
        self._forbidden_on_autopilot('updateOrder', *args, **kw)

    def _forbidden_on_autopilot(self, method, *args, **kw):
        if self.autopilot:
            raise RuntimeError("%s: '%s' is forbidden while on autopilot"
                               % (self, method))
        else:
            return getattr(super(TeaserList, self), method)(*args, **kw)

    @rwproperty.getproperty
    def autopilot(self):
        return self._autopilot

    @rwproperty.setproperty
    def autopilot(self, autopilot):
        if autopilot and self.referenced_cp is None:
            raise ValueError(
                'Cannot activate autopilot without referenced centerpage.')
        if autopilot == self._autopilot:
            return

        # we need to manipulate self.entries, which is only allowed while not
        # on autopilot. Thus we switch the autopilot mode at different times.
        if not autopilot:
            self._autopilot = autopilot
            if hasattr(self.xml, 'xi_include'):
                self.xml.remove(self.xml.xi_include)

            if self.referenced_cp:
                repository = zope.component.getUtility(
                    zeit.cms.repository.interfaces.IRepository)
                for position, id in enumerate(
                    zeit.content.cp.interfaces.ILeadTeasers(
                        self.referenced_cp)):
                    self.insert(position, repository.getContent(id))
        else:
            self.clear()
            # XXX what is the actual syntax for xi:include needed here?
            self.xml.append(lxml.objectify.E.xi_include(
                href=self.referenced_cp.uniqueId))
            self._autopilot = autopilot

    def clear(self):
        if not self.autopilot:
            for entry in self:
                self.remove(entry)

    @rwproperty.getproperty
    def layout(self):
        for layout in zeit.content.cp.layout.LayoutSource():
            if layout.id == self.xml.get('module'):
                return layout

    @rwproperty.setproperty
    def layout(self, layout):
        self.xml.set('module', layout.id)


TeaserListFactory = zeit.content.cp.block.blockFactoryFactory(
    zeit.content.cp.interfaces.IRegion,
    TeaserList, 'teaser', _('List of teasers'))


@zope.component.adapter(zeit.content.cp.interfaces.ICenterPage)
@zope.interface.implementer(zeit.content.cp.interfaces.ILeadTeasers)
def lead_teasers_for_centerpage(cp):
    result = []
    for block in cp['lead'].values():
        if zeit.content.cp.interfaces.ITeaserList.providedBy(block):
            try:
                result.append(iter(block).next().uniqueId)
            except StopIteration:
                pass
    return result


class Teaser(zeit.cms.content.metadata.CommonMetadata):

    zope.interface.implements(
        zeit.content.cp.interfaces.ITeaser)

    original_content = zeit.cms.content.property.SingleResource(
        '.original_content')

    default_template = u"""\
        <teaser
          xmlns:py="http://codespeak.net/lxml/objectify/pytype">
        </teaser>
    """

teaserFactory = zeit.cms.content.adapter.xmlContentFactory(Teaser)

resourceFactory = zeit.cms.connector.xmlContentToResourceAdapterFactory(
    'teaser')
resourceFactory = zope.component.adapter(
    zeit.content.cp.interfaces.ITeaser)(resourceFactory)


@zope.component.adapter(zeit.cms.content.interfaces.ICommonMetadata)
@zope.interface.implementer(zeit.content.cp.interfaces.ITeaser)
def metadata_to_teaser(content):
    teaser = Teaser()
    for name in zeit.cms.content.interfaces.ICommonMetadata:
        setattr(teaser, name, getattr(content, name))
    teaser.original_content = content
    return teaser
