import grokcore.component as grok
import zeit.cms.interfaces
import zeit.push.interfaces
import zope.component


class Message(grok.Adapter):

    grok.context(zeit.cms.interfaces.ICMSContent)
    grok.implements(zeit.push.interfaces.IMessage)
    grok.baseclass()

    get_text_from = NotImplemented

    def __init__(self, context):
        self.context = context
        self.config = {}

    def send(self):
        notifier = zope.component.getUtility(
            zeit.push.interfaces.IPushNotifier, name=self.type)
        notifier.send(self.text, self.url, **self.config)

    @property
    def type(self):
        return self.__class__.__dict__['grokcore.component.directive.name']

    @property
    def url(self):
        return self.context.uniqueId.replace(
            zeit.cms.interfaces.ID_NAMESPACE, 'http://www.zeit.de/')

    @property
    def text(self):
        push = zeit.push.interfaces.IPushMessages(self.context)
        text = getattr(push, self.get_text_from)
        limit = zeit.push.interfaces.IPushMessages[
            self.get_text_from].queryTaggedValue('zeit.cms.charlimit')
        if limit and len(text) > limit:
            text = text[:limit - 3] + u'...'
        return text


class OneTimeMessage(Message):
    """A Message that disables its service after it has been sent."""

    def send(self):
        super(OneTimeMessage, self).send()
        push = zeit.push.interfaces.IPushMessages(self.context)
        config = push.message_config[:]
        for service in config:
            if service == self.config:
                service['enabled'] = False
        push.message_config = config
