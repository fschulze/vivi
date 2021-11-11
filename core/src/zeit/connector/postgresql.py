from lazy import lazy
import zeit.connector.interfaces
import zope.interface


@zope.interface.implementer(zeit.connector.interfaces.ICachingConnector)
class Connector(object):
    def __init__(self, roots={}, prefix=u'http://xml.zeit.de/'):
        print("postgresql.Connector.__init__", roots, prefix)
        roots.setdefault('postgresql', 'vivi')
        self._roots = roots
        self._prefix = prefix

    @lazy
    def _webdav_connector(self):
        print("postgresql.Connector._webdav_connector")
        import zeit.connector.connector
        return zeit.connector.connector.Connector(self._roots, self._prefix)

    def _id2path(self, id):
        """Transform an id to a location, e.g.
             http://xml.zeit.de/2006/12/ -->
             http://zip4.zeit.de:9999/cms/work/2006/12/
           Just a textual transformation: replace _prefix with _root"""
        if not id.startswith(self._prefix):
            raise ValueError("Bad id %r (prefix is %r)" % (id, self._prefix))
        return id[len(self._prefix):]

    def __getitem__(self, id):
        cid = self._webdav_connector._get_cannonical_id(id)
        path = self._id2path(id)
        print(cid, path)
        return self._webdav_connector[id]

    def locked(self, id):
        return self._webdav_connector.locked(id)

    @classmethod
    def factory(cls):
        import zope.app.appsetup.product
        print("postgresql.Connector.factory")
        config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.connector')
        return cls({
            'default': config['document-store'],
            'search': config['document-store-search']})


class TransactionBoundCachingConnector(Connector):
    pass


def connectorFactory():
    """Factory for creating the connector with data from zope.conf."""
    print("postgresql.connectorFactory")
    import zope.app.appsetup.product
    config = zope.app.appsetup.product.getProductConfiguration(
        'zeit.connector')
    return Connector({
        'default': config['document-store'],
        'search': config['document-store-search']})


@zope.component.adapter(zeit.connector.interfaces.IResourceInvalidatedEvent)
def invalidate_cache(event):
    connector = zope.component.getUtility(
        zeit.connector.interfaces.IConnector)
    try:
        connector.invalidate_cache(event.id)
    except ValueError:
        # The connector isn't responsible for the id, or the id is just plain
        # invalid. There is nothing to invalidate then anyway.
        pass
