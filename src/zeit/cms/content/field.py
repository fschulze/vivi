# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import xml.dom.minidom

import lxml.etree
import lxml.objectify

import zope.interface
import zope.proxy
import zope.schema
import zope.schema.interfaces

import zeit.cms.content.cmssubset
from zeit.cms.i18n import MessageFactory as _


DEFAULT_MARKER = object()


class IXMLTree(zope.schema.interfaces.IField):
    """A field containing an lxml.objectified tree."""
    # This is here to avoid circular imports


class IXMLSnippet(zope.schema.interfaces.IField):
    """A field containing an xml-snippet."""


class InvalidXML(zope.schema.interfaces.ValidationError):
    __doc__ = _('Invalid structure.')


class _XMLBase(zope.schema.Field):

    zope.interface.implements(zope.schema.interfaces.IFromUnicode)

    def fromUnicode(self, str):
        try:
            return lxml.objectify.fromstring(str)
        except (lxml.etree.XMLSyntaxError, ValueError), e:
                raise zope.schema.ValidationError(e)

    def set(self, object, value):
        if self.readonly:
            raise TypeError("Can't set values on read-only fields "
                            "(name=%s, class=%s.%s)"
                            % (self.__name__,
                               object.__class__.__module__,
                               object.__class__.__name__))
        current_value = self.query(object, DEFAULT_MARKER)
        if (current_value is DEFAULT_MARKER
            or current_value.getparent() is None):
            setattr(object, self.__name__, value)
        else:
            current_value[:] = [value]


class XMLTree(_XMLBase):

    zope.interface.implements(IXMLTree)


class XMLSnippet(zope.schema.Text):

    zope.interface.implements(IXMLSnippet)

    def __init__(self, subset=None, **kwargs):
        if subset is None:
            subset = zeit.cms.content.cmssubset.CMS_SUBSET
        self.subset = subset
        super(XMLSnippet, self).__init__(**kwargs)

    def fromUnicode(self, value):
        if not isinstance(value, unicode):
            raise TypeError("Expected unicode, got %s" % type(value))
        value = self._filter(value)
        return super(XMLSnippet, self).fromUnicode(value)

    def _validate(self, value):
        super(XMLSnippet, self)._validate(value)
        if value != self._filter(value):
            raise InvalidXML()

    def _filter(self, value):
        if self.subset is not None:
            # We need a dom where we can append the values.
            dom = xml.dom.minidom.parseString('<xml/>')
            value = self.subset.filteredParse(value, dom.firstChild)
            value = u''.join(node.toxml() for node in value.childNodes)
        return value
