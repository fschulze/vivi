from zeit.cms.content.interfaces import WRITEABLE_LIVE
from zeit.cms.i18n import MessageFactory as _
import re
import urlparse
import zeit.cms.content.dav
import zeit.cms.interfaces
import zeit.cms.workflow.interfaces
import zeit.connector.interfaces
import zeit.workflow.interfaces
import zope.app.appsetup.product
import zope.authentication.interfaces
import zope.component
import zope.interface


class PublishInfo(object):
    """Workflow baseclass. No concrete content type should use this,
    but rather one of the subclasses like AssetWorkflow or ContentWorkflow.
    """

    zope.component.adapts(zeit.cms.interfaces.ICMSContent)
    zope.interface.implements(zeit.cms.workflow.interfaces.IPublishInfo)

    zeit.cms.content.dav.mapProperties(
        zeit.cms.workflow.interfaces.IPublishInfo,
        zeit.workflow.interfaces.WORKFLOW_NS,
        ('published', 'date_last_published', 'date_last_published_semantic',
         'locked', 'lock_reason'),
        use_default=True, writeable=WRITEABLE_LIVE)

    zeit.cms.content.dav.mapProperties(
        zeit.cms.workflow.interfaces.IPublishInfo,
        zeit.cms.interfaces.DOCUMENT_SCHEMA_NS,
        ('date_first_released',),
        writeable=WRITEABLE_LIVE)

    date_print_published = zeit.cms.content.dav.DAVProperty(
        zeit.cms.workflow.interfaces.IPublishInfo['date_print_published'],
        zeit.cms.interfaces.DOCUMENT_SCHEMA_NS,
        'print-publish',
        writeable=WRITEABLE_LIVE)

    error_messages = ()

    def __init__(self, context):
        self.context = context

    @property
    def last_published_by(self):
        log = zeit.objectlog.interfaces.ILog(self.context)
        for entry in reversed(list(log.get_log())):
            if entry.message == _('Published'):
                return entry.principal
        else:
            return None

    def can_publish(self):
        if self.matches_blacklist():
            self.error_messages = (
                _('publish-preconditions-blacklist',
                  mapping=self._error_mapping),)
            return zeit.cms.workflow.interfaces.CAN_PUBLISH_ERROR
        if self.locked:
            mapping = self._error_mapping
            mapping['reason'] = self.lock_reason
            self.error_messages = (
                _('publish-preconditions-locked', mapping=mapping),)
            return zeit.cms.workflow.interfaces.CAN_PUBLISH_ERROR

    def matches_blacklist(self):
        config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.workflow')
        blacklist = re.split(', *', config['blacklist'])
        path = urlparse.urlparse(self.context.uniqueId).path
        for item in blacklist:
            if item and path.startswith(item):
                return True
        return False

    @property
    def _error_mapping(self):
        return {
            'name': self.context.__name__,
            'id': self.context.uniqueId,
        }


class NotPublishablePublishInfo(PublishInfo):

    def can_publish(self):
        return zeit.cms.workflow.interfaces.CAN_PUBLISH_ERROR

    @property
    def error_messages(self):
        return (
            _('publish-preconditions-not-met', mapping=self._error_mapping),
        )


@zope.component.adapter(PublishInfo)
@zope.interface.implementer(zeit.connector.interfaces.IWebDAVProperties)
def workflowProperties(context):
    return zeit.connector.interfaces.IWebDAVProperties(context.context, None)


# XXX what's the proper place for this?
# XXX return null object insted of None?
def id_to_principal(principal_id):
    if principal_id is None:
        return None
    auth = zope.component.getUtility(
        zope.authentication.interfaces.IAuthentication)
    try:
        return auth.getPrincipal(principal_id)
    except zope.authentication.interfaces.PrincipalLookupError:
        return None


@zope.component.adapter(
    zeit.cms.workflow.interfaces.IPublishInfo,
    zeit.cms.content.interfaces.IDAVPropertyChangedEvent)
def log_workflow_changes(workflow, event):
    if event.field.__name__ != 'locked':
        return
    message = _('${name}: ${new_value}', mapping={
        'name': event.field.title,
        'old_value': event.old_value,
        'new_value': event.new_value,
    })
    log = zope.component.getUtility(zeit.objectlog.interfaces.IObjectLog)
    log.log(workflow.context, message)
