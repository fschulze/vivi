# Copyright (c) 2007-2010 gocept gmbh & co. kg
# See also LICENSE.txt

from zope.testing import doctest
import BaseHTTPServer
import __future__
import contextlib
import copy
import inspect
import os
import pkg_resources
import random
import re
import sys
import threading
import time
import urllib2
import zeit.connector.interfaces
import zope.app.appsetup.product
import zope.app.testing.functional
import zope.component
import zope.publisher.browser
import zope.security.management
import zope.security.testing
import zope.site.hooks
import zope.testing.renormalizing


def ZCMLLayer(
    config_file, module=None, name=None, allow_teardown=True,
    product_config=None):
    if module is None:
        module = stack = inspect.stack()[1][0].f_globals['__name__']
    if name is None:
        name = 'ZCMLLayer(%s)' % config_file
    if not config_file.startswith('/'):
        config_file = pkg_resources.resource_filename(module, config_file)
    def setUp(cls):
        cls.setup = zope.app.testing.functional.FunctionalTestSetup(
            config_file, product_config=product_config)

    def tearDown(cls):
        cls.setup.tearDownCompletely()
        if not allow_teardown:
            raise NotImplementedError

    layer = type(name, (object,), dict(
        __module__=module,
        setUp=classmethod(setUp),
        tearDown=classmethod(tearDown),
    ))
    return layer


def HTTPServerLayer(request_handler):
    """Factory for a layer which opens a HTTP port."""
    module = stack = inspect.stack()[1][0].f_globals['__name__']
    port = random.randint(30000, 40000)

    def setUp(cls):
        cls.httpd_running = True
        def run():
            server_address = ('localhost', port)
            httpd = BaseHTTPServer.HTTPServer(
                server_address, request_handler)
            while cls.httpd_running:
                httpd.handle_request()
        t = threading.Thread(target=run)
        t.daemon = True
        t.start()
        # XXX this is a little kludgy
        time.sleep(0.001)

    def tearDown(cls):
        cls.httpd_running = False
        try:
            urllib2.urlopen('http://localhost:%s/die' % port)
        except urllib2.URLError:
            pass

    layer = type('HTTPLayer(%s)' % port, (object,), dict(
        __module__=module,
        setUp=classmethod(setUp),
        tearDown=classmethod(tearDown),
    ))
    return layer, port


class BaseHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handler for testing which does not log to STDOUT."""

    def log_message(self, format, *args):
        pass


cms_layer = ZCMLLayer('ftesting.zcml')


checker = zope.testing.renormalizing.RENormalizing([
    (re.compile(r'\d{4} \d{1,2} \d{1,2}  \d\d:\d\d:\d\d'), '<FORMATTED DATE>'),
    (re.compile('0x[0-9a-f]+'), "0x..."),
    (re.compile(r'/\+\+noop\+\+[0-9a-f]+'), ''),
    (re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'),
     "<GUID>"),
])


def setUpDoctests(test):
    test.old_product_config = copy.deepcopy(
        zope.app.appsetup.product.saveConfiguration())
    config = test.globs.get('product_config', {})
    __traceback_info__ = (config,)
    setup_product_config(config)


def tearDown(test):
    zope.security.management.endInteraction()
    # only for functional tests
    if hasattr(test, 'globs'):
        old_site = test.globs.get('old_site')
        if old_site is not None:
            zope.site.hooks.setSite(old_site)
    connector = zope.component.getUtility(
        zeit.connector.interfaces.IConnector)
    connector._reset()
    old_config = getattr(test, 'old_product_config', None)
    if old_config is not None:
        zope.app.appsetup.product.restoreConfiguration(old_config)


def setup_product_config(product_config={}):
    cms_config = zope.app.appsetup.product._configs['zeit.cms'] = {}
    base_path = os.path.join(os.path.dirname(__file__), 'content')

    cms_config['source-serie'] = 'file://%s' % os.path.join(
        base_path, 'serie.xml')
    cms_config['source-navigation'] = 'file://%s' % os.path.join(
        base_path, 'navigation.xml')
    cms_config['source-print-ressort'] = 'file://%s' % os.path.join(
        base_path, 'print-ressort.xml')
    cms_config['source-keyword'] = 'file://%s' % os.path.join(
        base_path, 'zeit-ontologie-prism.xml')
    cms_config['source-products'] = 'file://%s' % os.path.join(
        base_path, 'products.xml')
    cms_config['source-badges'] = 'file://%s' % (
        pkg_resources.resource_filename(__name__, 'asset/badges.xml'),)

    cms_config['preview-prefix'] = 'http://localhost/preview-prefix'
    cms_config['live-prefix'] = 'http://localhost/live-prefix'
    cms_config['development-preview-prefix'] = (
        'http://localhost/development-preview-prefix')
    cms_config['workingcopy-preview-base'] = (
        u'http://xml.zeit.de/tmp/previews/')

    cms_config['suggest-keyword-email-address'] = 'none@testing'
    cms_config['suggest-keyword-real-name'] = 'Dr. No'

    zope.app.appsetup.product._configs.update(product_config)


optionflags = (doctest.REPORT_NDIFF +
               doctest.INTERPRET_FOOTNOTES +
               doctest.NORMALIZE_WHITESPACE +
               doctest.ELLIPSIS)


def DocFileSuite(*paths, **kw):
    kw['package'] = doctest._normalize_module(kw.get('package'))
    kw.setdefault('checker', checker)
    kw.setdefault('optionflags', optionflags)
    return doctest.DocFileSuite(*paths, **kw)


def FunctionalDocFileSuite(*paths, **kw):
    layer = kw.pop('layer', cms_layer)
    kw['package'] = doctest._normalize_module(kw.get('package'))
    kw['setUp'] = setUpDoctests
    kw['tearDown'] = tearDown
    kw.setdefault('globs', {})['product_config'] = kw.pop(
        'product_config', {})
    kw['globs']['with_statement'] = __future__.with_statement
    kw.setdefault('checker', checker)
    kw.setdefault('optionflags', optionflags)

    test = zope.app.testing.functional.FunctionalDocFileSuite(
        *paths, **kw)
    test.layer = layer

    return test


class FunctionalTestCase(zope.app.testing.functional.FunctionalTestCase):

    layer = cms_layer
    product_config = {}

    def setUp(self):
        super(FunctionalTestCase, self).setUp()
        self.old_product_config = copy.deepcopy(
            zope.app.appsetup.product.saveConfiguration())
        setup_product_config(self.product_config)
        zope.site.hooks.setSite(self.getRootFolder())
        zeit.cms.testing.create_interaction(u'zope.user')

    def tearDown(self):
        zeit.cms.testing.tearDown(self)
        zope.site.hooks.setSite(None)
        super(FunctionalTestCase, self).tearDown()


def click_wo_redirect(browser, *args, **kwargs):
    browser.mech_browser.set_handle_redirect(False)
    try:
        try:
            browser.getLink(*args, **kwargs).click()
        except urllib2.HTTPError, e:
            print str(e)
            print e.hdrs.get('location')
    finally:
        browser.mech_browser.set_handle_redirect(True)


def set_site(site=None):
    """Encapsulation of the getSite/setSite-dance.

    Sets the given site, preserves the old site in the globs,
    where it will be reset by our FunctionalDocFileSuite's tearDown.
    """

    globs = sys._getframe(1).f_locals
    globs['old_site'] = zope.site.hooks.getSite()
    if site is None:
        site = globs['getRootFolder']()
    zope.site.hooks.setSite(site)


def create_interaction(name=u'zope.user'):
    principal = zope.security.testing.Principal(name)
    request = zope.publisher.browser.TestRequest()
    request.setPrincipal(principal)
    zope.security.management.newInteraction(request)
    return principal


@contextlib.contextmanager
def interaction(principal_id=u'zope.user'):
    create_interaction(principal_id)
    yield
    zope.security.management.endInteraction()


@contextlib.contextmanager
def site(root):
    old_site = zope.site.hooks.getSite()
    zope.site.hooks.setSite(root)
    yield
    zope.site.hooks.setSite(old_site)
