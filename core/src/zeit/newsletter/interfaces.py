# Copyright (c) 2011-2014 gocept gmbh & co. kg
# See also LICENSE.txt

from zeit.cms.i18n import MessageFactory as _
import zeit.cms.content.interfaces
import zeit.cms.repository.interfaces
import zeit.cms.workflow.interfaces
import zeit.edit.interfaces
import zope.container.interfaces
import zope.interface


DAV_NAMESPACE = 'http://namespaces.zeit.de/CMS/newsletter'


class INewsletter(zeit.cms.content.interfaces.IXMLContent,
                  zope.container.interfaces.IReadContainer):

    subject = zope.schema.TextLine(title=_('Subject'))

    def send():
        """Sends emails for this newsletter."""

    def send_test(to):
        """Sends test email to the given address."""

    body = zope.interface.Attribute('The IBody of this newsletter')


class IBody(zeit.edit.interfaces.IArea):
    pass


class IGroup(zeit.edit.interfaces.IArea,
             zeit.edit.interfaces.IBlock):

    title = zope.schema.TextLine(title=_('Title'))


class ITeaser(zeit.edit.interfaces.IBlock):

    reference = zope.schema.Choice(
        source=zeit.cms.content.contentsource.cmsContentSource)


class IAdvertisement(zeit.edit.interfaces.IBlock):

    href = zope.schema.TextLine(title=_('Target URL'))

    title = zope.schema.TextLine(title=_('Title'))

    text = zope.schema.Text(title=_('Text'))

    image = zope.schema.Choice(
        source=zeit.content.image.interfaces.imageSource,
        required=False)


class INewsletterCategory(zeit.cms.repository.interfaces.IDAVContent):

    last_created = zope.schema.Datetime(
        title=_(u'Timestamp when the last newsletter object'
                ' in this category was created'))

    def create():
        """Creates a new newsletter object for this category."""

    subject = zope.schema.TextLine(
        title=_(u'Subject'),
        description=_(u'{today} -> %d.%m.%Y'))

    mandant = zope.schema.Int(
        title=_(u'Optivo Mandant ID'))

    recipientlist = zope.schema.TextLine(
        title=_(u'Name of recipient list'))

    recipientlist_test = zope.schema.TextLine(
        title=_(u'Name of test-recipient list'),
        required=False)

    video_playlist = zope.schema.TextLine(
        title=_('Unique id of video playlist'),
        required=False)


class IRepositoryCategory(
        INewsletterCategory, zeit.cms.repository.interfaces.IFolder):
    pass


class ILocalCategory(
        INewsletterCategory, zeit.cms.workingcopy.interfaces.ILocalContent):
    """Local version of a newsletter category.

    The local version only holds the metadata, therefore it is not a container.
    """


class IBuild(zope.interface.Interface):
    """Builds a newsletter in a way specific to the category."""

    def __call__(content_list):
        """Selects appropriate content objects and populates the newsletter
        with groups and teasers."""


class INewsletterWorkflow(zeit.cms.workflow.interfaces.IPublishInfo):

    sent = zope.schema.Bool(title=_('Sent'), readonly=True)


class ITestRecipient(zope.interface.Interface):

    # XXX validate email?
    email = zope.schema.TextLine(title=_('Email for test'))


class IRenderer(zope.interface.Interface):

    def __call__(content):
        """Returns a dict with the keys html and text containing the rendered
        newsletter"""
