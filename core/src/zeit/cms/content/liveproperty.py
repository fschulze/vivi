from zeit.cms.content.interfaces import WRITEABLE_ALWAYS, WRITEABLE_LIVE
from zeit.cms.content.interfaces import WRITEABLE_ON_CHECKIN
import UserDict
import zeit.cms.checkout.interfaces
import zeit.cms.repository.interfaces
import zeit.connector.interfaces
import zope.component
import zope.interface
import zope.security.interfaces


class LiveProperties(object, UserDict.DictMixin):
    """Webdav properties which are updated upon change."""

    zope.component.adapts(zeit.cms.repository.interfaces.IRepositoryContent)
    zope.interface.implements(zeit.connector.interfaces.IWebDAVProperties)
    zope.interface.classProvides(
        zeit.cms.content.interfaces.ILivePropertyManager)

    live_properties = dict()

    def __init__(self, context):
        self.context = context

    def __repr__(self):
        return object.__repr__(self)

    def __getitem__(self, key):
        return self.resource.properties[key]

    def keys(self):
        return self.resource.properties.keys()

    def __contains__(self, key):
        return key in self.resource.properties

    def __setitem__(self, key, value):
        if not self.is_writeable_live(*key):
            raise zope.security.interfaces.Forbidden(key)
        if self.get(key, self) != value:  # use self as marker
            # Only call DAV when there actually is a change
            self.connector.changeProperties(
                self.context.uniqueId, {key: value})

    @property
    def resource(self):
        return self.connector[self.context.uniqueId]

    @property
    def connector(self):
        return zope.component.getUtility(zeit.connector.interfaces.IConnector)

    # ILivePropertyManager

    @classmethod
    def register_live_property(cls, name, namespace, writeable):
        cls.live_properties[(name, namespace)] = writeable

    @classmethod
    def unregister_live_property(cls, name, namespace):
        del cls.live_properties[(name, namespace)]

    @classmethod
    def is_writeable_live(cls, name, namespace):
        writeable = cls.live_properties.get((name, namespace))
        return writeable in [WRITEABLE_LIVE, WRITEABLE_ALWAYS]

    @classmethod
    def is_writeable_on_checkin(cls, name, namespace):
        writeable = cls.live_properties.get((name, namespace))
        return writeable in [WRITEABLE_ON_CHECKIN, WRITEABLE_ALWAYS]


@zope.component.adapter(
    zope.interface.Interface,
    zeit.cms.checkout.interfaces.IBeforeCheckinEvent)
def remove_live_properties(context, event):
    """Remove live properties from content.

    This is to make sure they don't change on checkin.

    """
    try:
        properties = zeit.connector.interfaces.IWebDAVProperties(context)
    except TypeError:
        return
    manager = zope.component.getUtility(
        zeit.cms.content.interfaces.ILivePropertyManager)
    for live_property in manager.live_properties:
        if not manager.is_writeable_on_checkin(*live_property):
            properties.pop(live_property, None)


@zope.component.adapter(LiveProperties)
@zope.interface.implementer(zeit.cms.interfaces.ICMSContent)
def live_to_cmscontent(context):
    return zeit.cms.interfaces.ICMSContent(context.context, None)
