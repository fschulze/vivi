# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import os
import unittest

import zope.app.testing.functional
from zope.testing import doctest

import zeit.cms.testing


ConnectorProfilingLayer = zope.app.testing.functional.ZCMLLayer(
    os.path.join(os.path.dirname(__file__), 'profiling.zcml'),
    __name__, 'ConnectorProfilingLayer', allow_teardown=True)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(zeit.cms.testing.FunctionalDocFileSuite(
        'full-profiling.txt',
        layer=ConnectorProfilingLayer))
    return suite
