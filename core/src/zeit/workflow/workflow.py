# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import datetime

import pytz
import rwproperty

import zope.component
import zope.event
import zope.interface

import zeit.connector.interfaces
import zeit.cms.interfaces
import zeit.cms.content.dav
import zeit.cms.content.interfaces

import zeit.workflow.interfaces


class LiveProperties(dict):
    """Webdav properties which are updated upon change."""

    def __init__(self, resource):
        super(LiveProperties, self).__init__(resource.properties)
        self.resource_id = resource.id

    def __setitem__(self, key, value):
        super(LiveProperties, self).__setitem__(key, value)
        self.connector.changeProperties(self.resource_id, {key: value})

    @property
    def connector(self):
        return zope.component.getUtility(zeit.cms.interfaces.IConnector)


class Workflow(object):
    """Adapt ICMSContent to IWorkflow using the "live" data from connector.

    We must read and write properties directly from the DAV to be sure we
    actually can do the transition.
    """

    zope.interface.implements(zeit.workflow.interfaces.IWorkflow)
    zope.component.adapts(zeit.cms.interfaces.ICMSContent)

    zeit.cms.content.dav.mapProperties(
        zeit.workflow.interfaces.IWorkflow,
        'http://namespaces.zeit.de/CMS/workflow',
        ('edited', 'corrected', 'refined', 'published',
         'images_added', 'urgent'))

    zeit.cms.content.dav.mapProperty(
        zeit.workflow.interfaces.IWorkflow['release_period'].fields[0],
        'http://namespaces.zeit.de/CMS/workflow',
        'released_from')
    zeit.cms.content.dav.mapProperty(
        zeit.workflow.interfaces.IWorkflow['release_period'].fields[1],
        'http://namespaces.zeit.de/CMS/workflow',
        'released_to')

    zeit.cms.content.dav.mapProperties(
        zeit.workflow.interfaces.IWorkflow,
        'http://namespaces.zeit.de/CMS/document',
        ('date_first_released', 'last_modified_by'))

    def __init__(self, context):
        self.context = context
        resource = self.connector[self.context.uniqueId]
        self.properties = LiveProperties(resource)

    @property
    def connector(self):
        return zope.component.getUtility(zeit.cms.interfaces.IConnector)

    @rwproperty.getproperty
    def release_period(self):
        return self.released_from, self.released_to

    @rwproperty.setproperty
    def release_period(self, value):
        if value is None:
            value = None, None
        self.released_from, self.released_to = value


@zope.component.adapter(zeit.workflow.interfaces.IWorkflow)
@zope.interface.implementer(zeit.cms.interfaces.IWebDAVProperties)
def workflowProperties(context):
    return context.properties


class FeedMetadataUpdater(object):
    """Add the expire/publication time to feed entry."""

    zope.interface.implements(
        zeit.cms.syndication.interfaces.IFeedMetadataUpdater)

    def update_entry(self, entry, content):
        workflow = zeit.workflow.interfaces.IWorkflow(content, None)
        if workflow is None:
            return

        date = ''
        if workflow.released_from:
            date = workflow.released_from.isoformat()
        entry.set('publication-date', date)

        date = ''
        if workflow.released_to:
            date = workflow.released_to.isoformat()
        entry.set('expires', date)


@zope.component.adapter(
    zeit.workflow.interfaces.IWorkflow,
    zeit.cms.content.interfaces.IDAVPropertyChangedEvent)
def set_first_release_date(context, event):
    # XXX refactor to use a IPublishedEvent.
    if ((event.property_name, event.property_namespace) !=
        ('published', 'http://namespaces.zeit.de/CMS/workflow')):
        return
    if context.date_first_released:
        return
    context.date_first_released = datetime.datetime.now(pytz.UTC)


@zope.component.adapter(
    zope.interface.Interface,
    zeit.cms.checkout.interfaces.IBeforeCheckinEvent)
def update_last_modified_by(context, event):
    workflow = zeit.workflow.interfaces.IWorkflow(context, None)
    if workflow is None:
        return
    workflow.last_modified_by = event.principal.id


@zope.component.adapter(
    zeit.workflow.interfaces.IWorkflow,
    zeit.cms.content.interfaces.IDAVPropertyChangedEvent)
def notify_adapted_property_change(context, event):
    """Notify the object IWorkflow adapted about a property change."""
    content = context.context
    zope.event.notify(
        zeit.cms.content.interfaces.DAVPropertyChangedEvent(
            content, event.property_namespace, event.property_name,
            event.old_value, event.new_value))


@zope.component.adapter(
    zope.interface.Interface,
    zeit.cms.checkout.interfaces.IBeforeCheckinEvent)
def remove_live_properties(context, event):
    """Remove live properties from content.

    This is to make sure they don't change on checkin.

    """
    properties = zeit.connector.interfaces.IWebDAVProperties(context)
    for name, namespace in list(properties):  # make sure it's not an iterator
        if namespace == 'http://namespaces.zeit.de/CMS/workflow':
            # XXX use a string constant wor the namespace
            del properties[(name, namespace)]
