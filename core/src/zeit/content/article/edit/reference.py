# Copyright (c) 2010 gocept gmbh & co. kg
# See also LICENSE.txt

from zeit.cms.i18n import MessageFactory as _
import grokcore.component
import zeit.cms.content.interfaces
import zeit.cms.interfaces
import zeit.content.article.edit.block
import zeit.content.article.edit.interfaces
import zeit.content.gallery.interfaces
import zeit.content.infobox.interfaces
import zeit.edit.block
import zeit.edit.interfaces
import zope.component
import zope.schema


class Reference(zeit.edit.block.SimpleElement):

    area = zeit.content.article.edit.interfaces.IEditableBody
    grokcore.component.baseclass()

    @property
    def references(self):
       return zeit.cms.interfaces.ICMSContent(self.xml.get('href'), None)

    @references.setter
    def references(self, value):
        if value is None:
            # clear everything to be sure we don't expose any false
            # informationn when another object is set later
            name = self.__name__
            self.xml.attrib.clear()
            self.__name__ = name
            for child in self.xml.getchildren():
                self.xml.remove(child)
        else:
            self._validate(value)
            self.xml.set('href', value.uniqueId)
            updater = zeit.cms.content.interfaces.IXMLReferenceUpdater(
                value, None)
            if updater is not None:
                updater.update(self.xml)

    def _validate(self, value):
        field = zope.interface.providedBy(self).declared[0]['references']
        field = field.bind(self)
        field.validate(value)


class Gallery(Reference):

    grokcore.component.implements(
        zeit.content.article.edit.interfaces.IGallery)
    type = 'gallery'


class GalleryFactory(zeit.content.article.edit.block.BlockFactory):

    produces = Gallery
    title = _('Gallery')


@grokcore.component.adapter(zeit.content.article.edit.interfaces.IEditableBody,
                            zeit.content.gallery.interfaces.IGallery)
@grokcore.component.implementer(zeit.edit.interfaces.IElement)
def factor_block_from_gallery(body, context):
    block = GalleryFactory(body)()
    block.references = context
    return block


class Infobox(Reference):

    grokcore.component.implements(
        zeit.content.article.edit.interfaces.IInfobox)
    type = 'infobox'


class InfoboxFactory(zeit.content.article.edit.block.BlockFactory):

    produces = Infobox
    title = _('Infobox')


@grokcore.component.adapter(zeit.content.article.edit.interfaces.IEditableBody,
                            zeit.content.infobox.interfaces.IInfobox)
@grokcore.component.implementer(zeit.edit.interfaces.IElement)
def factor_block_from_infobox(body, context):
    block = InfoboxFactory(body)()
    block.references = context
    return block
