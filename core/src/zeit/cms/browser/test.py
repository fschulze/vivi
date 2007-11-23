# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from zope.testing import doctest

import zeit.cms.testing

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(zeit.cms.testing.FunctionalDocFileSuite(
        'listing.txt', 'README.txt', 'error-views.txt',
        optionflags=(doctest.REPORT_NDIFF + doctest.NORMALIZE_WHITESPACE +
                     doctest.ELLIPSIS)))
    suite.addTest(doctest.DocFileSuite(
        'widget.txt',
        optionflags=(doctest.REPORT_NDIFF + doctest.NORMALIZE_WHITESPACE +
                     doctest.ELLIPSIS)))
    return suite
