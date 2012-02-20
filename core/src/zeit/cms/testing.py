# Copyright (c) 2007-2012 gocept gmbh & co. kg
# See also LICENSE.txt

from zope.testing import doctest
import BaseHTTPServer
import __future__
import contextlib
import copy
import gocept.jslint
import gocept.selenium.ztk
import gocept.testing.assertion
import inspect
import json
import logging
import mock
import pkg_resources
import random
import re
import string
import sys
import threading
import time
import transaction
import unittest2
import urllib2
import xml.sax.saxutils
import zeit.connector.interfaces
import zope.app.appsetup.product
import zope.app.testing.functional
import zope.component
import zope.publisher.browser
import zope.security.management
import zope.security.testing
import zope.site.hooks
import zope.testbrowser.testing
import zope.testing.renormalizing


def ZCMLLayer(
    config_file, module=None, name=None, allow_teardown=True,
    product_config=None):
    if module is None:
        module = inspect.stack()[1][0].f_globals['__name__']
    if name is None:
        name = 'ZCMLLayer(%s)' % config_file
    if not config_file.startswith('/'):
        config_file = pkg_resources.resource_filename(module, config_file)
    if product_config is True:
        product_config = cms_product_config

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


class HTTPServer(BaseHTTPServer.HTTPServer):
    # shutdown mechanism borrowed from gocept.selenium.static.HTTPServer

    _continue = True

    def __init__(self, *args):
        BaseHTTPServer.HTTPServer.__init__(self, *args)
        self.errors = []

    def handle_error(self, request, client_address):
        self.errors.append((request, client_address))

    def serve_until_shutdown(self):
        while self._continue:
            self.handle_request()

    def shutdown(self):
        self._continue = False
        # We fire a last request at the server in order to take it out of the
        # while loop in `self.serve_until_shutdown`.
        try:
            urllib2.urlopen(
                'http://%s:%s/die' % (self.server_name, self.server_port),
                timeout=1)
        except urllib2.URLError:
            # If the server is already shut down, we receive a socket error,
            # which we ignore.
            pass
        self.server_close()


def HTTPServerLayer(request_handler):
    """Factory for a layer which opens a HTTP port."""
    module = inspect.stack()[1][0].f_globals['__name__']
    port = random.randint(30000, 40000)

    def setUp(cls):
        server_address = ('localhost', port)
        cls.httpd = HTTPServer(server_address, request_handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_until_shutdown)
        cls.thread.daemon = True
        cls.thread.start()
        # Wait as it sometimes takes a while to get the server started.
        # XXX this is a little kludgy
        time.sleep(0.001)

    def tearDown(cls):
        cls.httpd.shutdown()
        cls.thread.join()

    def testTearDown(cls):
        cls.httpd.errors[:] = []
        request_handler.tearDown()

    layer = type('HTTPLayer(%s)' % port, (object,), dict(
        __module__=module,
        setUp=classmethod(setUp),
        tearDown=classmethod(tearDown),
        testTearDown=classmethod(testTearDown),
    ))
    return layer, port


class BaseHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handler for testing which does not log to STDOUT."""

    def log_message(self, format, *args):
        pass

    @classmethod
    def tearDown(cls):
        pass


cms_product_config = string.Template("""\
<product-config zeit.cms>
  source-serie file://${base}/content/serie.xml
  source-navigation file://${base}/content/navigation.xml
  source-print-ressort file://${base}/content/print-ressort.xml
  source-keyword file://${base}/content/zeit-ontologie-prism.xml
  source-products file://${base}/content/products.xml
  source-badges file://${base}/asset/badges.xml

  preview-prefix http://localhost/preview-prefix
  live-prefix http://localhost/live-prefix
  development-preview-prefix http://localhost/development-preview-prefix

  suggest-keyword-email-address none@testing
  suggest-keyword-real-name Dr. No
  whitelist-url file://${base}/tagging/tests/whitelist.xml
</product-config>
""").substitute(
    base=pkg_resources.resource_filename(__name__, ''))


cms_layer = ZCMLLayer('ftesting.zcml', product_config=True)
selenium_layer = gocept.selenium.ztk.Layer(cms_layer)


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


class RepositoryHelper(object):

    @property
    def repository(self):
        import zeit.cms.repository.interfaces
        with site(self.getRootFolder()):
            return zope.component.getUtility(
                zeit.cms.repository.interfaces.IRepository)

    @repository.setter
    def repository(self, value):
        self.__dict__['repository'] = value


class ZCAHelper(object):

    def patchUtility(self, interface, new=None, name=None, sm=None):
        self._ensure_storage()
        if sm is None:
            sm = zope.component.getSiteManager()
        if new is None:
            new = mock.Mock()
        orig = sm.queryUtility(interface)
        if orig is not None:
            self.utilities.append((sm, orig, interface, name))
        if name is None:
            sm.registerUtility(new, interface)
        else:
            sm.registerUtility(new, interface, name)
        return new

    def restoreUtilities(self):
        self._ensure_storage()
        for sm, orig, interface, name in self.utilities:
            if name is None:
                sm.registerUtility(orig, interface)
            else:
                sm.registerUtility(orig, interface, name)

    def _ensure_storage(self):
        if not hasattr(self, 'utilities'):
            self.utilities = []


class FunctionalTestCase(zope.app.testing.functional.FunctionalTestCase,
                         unittest2.TestCase,
                         gocept.testing.assertion.Exceptions,
                         RepositoryHelper,
                         ZCAHelper):

    layer = cms_layer
    product_config = {}

    def setUp(self):
        super(FunctionalTestCase, self).setUp()
        self.old_product_config = copy.deepcopy(
            zope.app.appsetup.product.saveConfiguration())
        setup_product_config(self.product_config)
        zope.site.hooks.setSite(self.getRootFolder())
        self.principal = zeit.cms.testing.create_interaction(u'zope.user')

    def tearDown(self):
        self.restoreUtilities()
        zeit.cms.testing.tearDown(self)
        zope.site.hooks.setSite(None)
        super(FunctionalTestCase, self).tearDown()


class SeleniumTestCase(gocept.selenium.ztk.TestCase,
                       unittest2.TestCase,
                       RepositoryHelper):

    layer = selenium_layer
    skin = 'cms'
    log_errors = False
    log_errors_ignore = ()
    level = 2

    def setUp(self):
        super(SeleniumTestCase, self).setUp()
        if self.log_errors:
            with site(self.getRootFolder()):
                error_log = zope.component.getUtility(
                    zope.error.interfaces.IErrorReportingUtility)
                error_log.copy_to_zlog = True
                error_log._ignored_exceptions = self.log_errors_ignore
            self.log_handler = logging.StreamHandler(sys.stdout)
            logging.root.addHandler(self.log_handler)
            self.old_log_level = logging.root.level
            logging.root.setLevel(logging.ERROR)
            transaction.commit()
        self.selenium.getEval('window.sessionStorage.clear()')

    def tearDown(self):
        zeit.cms.testing.tearDown(self)
        super(SeleniumTestCase, self).tearDown()
        if self.log_errors:
            logging.root.removeHandler(self.log_handler)
            logging.root.setLevel(self.old_log_level)

    def open(self, path, auth='user:userpw'):
        auth_sent = getattr(self.layer, 'auth_sent', None)
        if auth and auth != auth_sent:
            # Only set auth when it changed. Firefox will be confused
            # otherwise.
            self.layer.auth_sent = auth
            auth = auth + '@'
        else:
            auth = ''
        self.selenium.open(
            'http://%s%s/++skin++%s%s' % (
                auth, self.selenium.server, self.skin, path))

    def click_label(self, label):
        self.selenium.click('//label[contains(string(.), %s)]' %
                            xml.sax.saxutils.quoteattr(label))


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


# XXX use zope.publisher.testing for the following two
def create_interaction(name=u'zope.user'):
    principal = zope.security.testing.Principal(
        name, groups=['zope.Authenticated'], description=u'test@example.com')
    request = zope.publisher.browser.TestRequest()
    request.setPrincipal(principal)
    zope.security.management.newInteraction(request)
    return principal


@contextlib.contextmanager
def interaction(principal_id=u'zope.user'):
    if zope.security.management.queryInteraction():
        # There already is an interaction. Great. Leave it alone.
        yield
    else:
        principal = create_interaction(principal_id)
        yield principal
        zope.security.management.endInteraction()


# XXX use zope.component.testing.site instead
@contextlib.contextmanager
def site(root):
    old_site = zope.site.hooks.getSite()
    zope.site.hooks.setSite(root)
    yield
    zope.site.hooks.setSite(old_site)


class BrowserAssertions(gocept.testing.assertion.Ellipsis):

    # XXX backwards-compat method signature for existing tests, should probably
    # be removed at some point
    def assert_ellipsis(self, want, got=None):
        if got is None:
            got = self.browser.contents
        self.assertEllipsis(want, got)

    def assert_json(self, want, got=None):
        if got is None:
            got = self.browser.contents
        data = json.loads(got)
        self.assertEqual(want, data)
        return data


class BrowserTestCase(FunctionalTestCase,
                      gocept.testing.assertion.Exceptions,
                      BrowserAssertions):

    def setUp(self):
        super(BrowserTestCase, self).setUp()
        # undo some setup that would break browser tests
        zope.security.management.endInteraction()
        zope.component.hooks.setSite(None)

        self.browser = zope.testbrowser.testing.Browser()
        self.browser.addHeader('Authorization', 'Basic user:userpw')


class JSLintTestCase(gocept.jslint.TestCase):

    options = (gocept.jslint.TestCase.options +
               ('--eqeq',
                '--evil',
                '--forin',
                '--plusplus',
                '--predef='
                'zeit,gocept,application_url,context_url,'
                'jQuery,DOMParser,'
                'console,'
                'alert,confirm,prompt,escape,unescape,getSelection,'
                'jsontemplate,'
                'MochiKit,$,$$,forEach,filter,map,extend,bind,'
                'log,repr,logger,logDebug,logError,' # XXX
                'DIV,A,UL,LI,INPUT,IMG,SELECT,OPTION,BUTTON,'
                'isNull,isUndefined,isUndefinedOrNull',
                ))

    ignore = (
        "Avoid 'arguments.callee'",
        "Compare with undefined, or use the hasOwnProperty method instead",
        "Do not use 'new' for side effects",
        "Don't make functions within a loop",
        "Expected an identifier and instead saw 'import'",
        "This is an ES5 feature",
        "Use a named parameter",
        "unused variable: self",
        "Missing radix parameter",
        )
