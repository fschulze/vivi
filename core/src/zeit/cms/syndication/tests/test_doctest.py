# Copyright (c) 2007-2011 gocept gmbh & co. kg
# See also LICENSE.txt

import zeit.cms.testing


def test_suite():
    return zeit.cms.testing.FunctionalDocFileSuite(
        'README.txt',
        'feed.txt',
        'oldchannel.txt',
        package='zeit.cms.syndication'
    )
