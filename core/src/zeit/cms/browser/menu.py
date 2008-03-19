# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import zope.viewlet.viewlet

import zope.app.pagetemplate
import zope.app.publisher.browser.menu
import zope.app.publisher.interfaces.browser

import z3c.menu.simple.menu

from zeit.cms.i18n import MessageFactory as _


class ExternalActionsMenu(zope.app.publisher.browser.menu.BrowserMenu):

    def getMenuItems(self, object, request):
        result = super(ExternalActionsMenu, self).getMenuItems(object, request)
        for item in result:
            item['target'] = "_blank"
        return result


class MenuItem(zope.viewlet.viewlet.ViewletBase):

    sort = 0

    def __cmp__(self, other):
        return cmp(float(self.sort), float(other.sort))


class MenuViewlet(MenuItem):

    menu = None

    @property
    def menu_items(self):
        menu = zope.component.getUtility(
            zope.app.publisher.interfaces.browser.IBrowserMenu,
            name=self.menu)
        return menu.getMenuItems(self.context, self.request)


class GlobalMenuItem(z3c.menu.simple.menu.GlobalMenuItem):
    """A menu item in the global menu."""

    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'globalmenuitem.pt')

    activeCSS = 'selected'
    inActiveCSS = ''
    pathitem = ''

    @property
    def selected(self):
        app_url = self.request.getApplicationURL()
        url = self.request.getURL()
        path = url[len(app_url):].split('/')
        if path and self.pathitem in path:
            return True

        return False


class CMSMenuItem(GlobalMenuItem):
    """The CMS menu item which is active when no other item is active."""

    title = _("CMS")
    viewURL = "@@index.html"

    @property
    def selected(self):
        result = 0
        for viewlet in self.manager.viewlets:
            if viewlet.pathitem and not viewlet.selected:
                result += 1
            elif viewlet.pathitem and viewlet.selected:
                result -= 1

        return result > 0


class LightboxActionMenuItem(MenuItem, z3c.menu.simple.menu.SimpleMenuItem):

    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'action-menu-item-with-lightbox.pt')
