# Copyright (c) 2007-2010 gocept gmbh & co. kg
# See also LICENSE.txt

import zeit.cms.content.dav
import grokcore.component
import zeit.cms.interfaces
import zeit.connector.interfaces
import zeit.content.portraitbox.interfaces
import zope.component
import zope.interface


class PortraitboxReference(zeit.cms.content.dav.DAVPropertiesAdapter):

    #grokcore.component.context(zeit.cms.interfaces.ICMSContent)
    grokcore.component.implements(
        zeit.content.portraitbox.interfaces.IPortraitboxReference)

    portraitbox = zeit.cms.content.dav.DAVProperty(
        zeit.content.portraitbox.interfaces.IPortraitboxReference[
            'portraitbox'],
        zeit.cms.interfaces.DOCUMENT_SCHEMA_NS, 'artbox_portrait')
