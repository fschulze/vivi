from zeit.cms.i18n import MessageFactory as _
import commentjson
import zeit.cms.content.dav
import zeit.cms.interfaces
import zeit.content.text.interfaces
import zeit.content.text.text
import zope.interface


@zope.interface.implementer(zeit.content.text.interfaces.IJSON)
class JSON(zeit.content.text.text.Text):

    @property
    def data(self):
        return commentjson.loads(self.text)


class JSONType(zeit.content.text.text.TextType):

    interface = zeit.content.text.interfaces.IJSON
    type = 'json'
    title = _('JSON file')
    factory = JSON
    addform = zeit.cms.type.SKIP_ADD


@zope.interface.implementer(
    zeit.content.text.interfaces.IValidationSchema)
class ValidationSchema(zeit.cms.content.dav.DAVPropertiesAdapter):

    schema_url = zeit.cms.content.dav.DAVProperty(
        zeit.content.text.interfaces.IValidationSchema['schema_url'],
        zeit.cms.interfaces.DOCUMENT_SCHEMA_NS,
        'schema_url')
