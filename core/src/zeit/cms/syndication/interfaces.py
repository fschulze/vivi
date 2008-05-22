# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import zope.component
import zope.component.interfaces
import zope.interface
import zope.schema

import zc.sourcefactory.contextual

import zeit.cms.content.contentsource
import zeit.cms.content.interfaces
import zeit.cms.relation.interfaces
from zeit.cms.i18n import MessageFactory as _


class ISyndicationManager(zope.interface.Interface):
    """Manages syndication of a content object."""

    targets = zope.interface.Attribute("List possible syndication targets.")

    canSyndicate = zope.interface.Attribute(
        "True if the object can be syndicated; False otherwise.")

    def syndicate(targets):
        """Syndicate the managed object to the given targets.

        raises SyndicationError if the object could not be syndicated.

        """


class IReadFeed(zope.interface.Interface):
    """Feed read interface."""

    title = zope.schema.TextLine(title=_("Title"))
    object_limit = zope.schema.Int(
        title=_("Limit amount"),
        description=_("limit-amount-description"),
        default=50,
        min=1,
        required=False)

    def pinned(content):
        """Returns true, if content is pinned"""

    def hidden(content):
        """Returns true, if the content is hidden on the homepage."""

    def __len__():
        """Return amount of objects syndicated."""

    def __iter__():
        """Iterate over published content.

        When content is pinned __iter__ is supposed to return pinned content
        at the right position.

        """

    def getPosition(content):
        """Returns the position of `content` in the feed.

        Returns 1-based position of the content object in the feed or None if
        the content is not syndicated in this feed.

        """


class IWriteFeed(zope.interface.Interface):
    """Feed write interface."""

    def insert(index, content):
        """Add `content` to self at position `index`."""

    def remove(content):
        """Remove `content` from feed."""

    def pin(content):
        """Pin `content` to current position."""

    def unpin(content):
        """Remove pining for `content`. """

    def hide(content):
        """Hide `content` on homepage."""

    def show(content):
        """Show `content on homepage."""

    def updateOrder(order):
        """Revise the order of keys, replacing the current ordering.

        order is a list or a tuple containing the set of existing keys in
        the new order. `order` must contain ``len(keys())`` items and cannot
        contain duplicate keys.

        Raises ``ValueError`` if order contains an invalid set of keys.
        """

    def updateMetadata(self, content):
        """Update the metadata of a contained object.

        Raises KeyError if the content is not syndicated in this feed.

        """

class IFeed(IReadFeed, IWriteFeed):
    """Documents can be published into a feed."""


class IContentSyndicatedEvent(zope.component.interfaces.IObjectEvent):
    """Issued when an object is syndicated."""

    targets = zope.schema.Set(
        title=u"The syndication target.",
        value_type=zope.schema.Object(IFeed))


class ContentSyndicatedEvent(zope.component.interfaces.ObjectEvent):
    """Issued when an object is syndicated."""

    zope.interface.implements(IContentSyndicatedEvent)

    def __init__(self, object, targets):
        super(ContentSyndicatedEvent, self).__init__(object)
        self.targets = set(targets)


class SyndicationError(Exception):
    """Raised when there is an error during syndication."""


class IMySyndicationTargets(zope.interface.Interface):

    targets = zope.schema.Tuple(
        title=_("Syndication targets"),
        default=(),
        required=False,
        value_type=zope.schema.Object(IFeed))


class IFeedMetadataUpdater(zope.interface.Interface):
    """Update feed entry metadata.
    """

    def update_entry(entry, obj):
        """Update entry with data from obj.

        Entry: lxml.objectify'ed element from the feed.
        obj: the object to be updated.

        """


class IFeedSource(zeit.cms.content.interfaces.ICMSContentSource):
    """A source for feeds."""


class FeedSource(zeit.cms.content.contentsource.CMSContentSource):

    zope.interface.implements(IFeedSource)
    name = 'zeit.cms.syndication.feed'

    def verify_interface(self, value):
        return IFeed.providedBy(value)


feedSource = FeedSource()


class SyndicatedInSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """A source returning the feeds an article is syndicated in."""

    def getValues(self, context):
        relations = zope.component.getUtility(
            zeit.cms.relation.interfaces.IRelations)
        return relations.get_relations(context, 'syndicated_in')

    def getTitle(self, context, value):
        return value.title


class IAutomaticMetadataUpdate(zope.interface.Interface):
    """Access to information about automatic metadata update."""

    automaticMetadataUpdateDisabled = zope.schema.FrozenSet(
        title=_("No automatic metadata update"),
        description=_("When this object is checked in, its metata will "
                      "not automatically updated in the selected channels."),
        default=frozenset(),
        value_type=zope.schema.Choice(source=SyndicatedInSource()))

