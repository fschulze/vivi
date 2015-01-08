from zeit.cms.repository.interfaces import IRepositoryContent
import lovely.remotetask.interfaces
import zeit.cms.browser.menu
import zeit.cms.workflow.interfaces
import zope.component


class PublishMenuItem(zeit.cms.browser.menu.LightboxActionMenuItem):

    sort = -1
    lightbox = '@@publish.html'

    def render(self):
        return super(PublishMenuItem, self).render()


class Publish(object):

    def can_publish(self):
        info = zeit.cms.workflow.interfaces.IPublishInfo(self.context)
        return info.can_publish()


class FlashPublishErrors(zeit.cms.browser.view.Base):

    def __call__(self, job):
        job = int(job)
        tasks = zope.component.getUtility(
            lovely.remotetask.interfaces.ITaskService, name='general')
        if tasks.getStatus(job) != lovely.remotetask.interfaces.COMPLETED:
            return
        error = tasks.getResult(job)
        if error is not None:
            self.send_message(error, type='error')


class RetractMenuItem(zeit.cms.browser.menu.LightboxActionMenuItem):

    sort = 200
    lightbox = '@@retract.html'

    @property
    def visible(self):
        info = zeit.cms.workflow.interfaces.IPublishInfo(self.context)
        return info.published

    def render(self):
        if not self.visible or not IRepositoryContent.providedBy(self.context):
            return ''
        else:
            return super(RetractMenuItem, self).render()
