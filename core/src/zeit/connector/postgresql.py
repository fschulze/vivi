import zeit.connector.interfaces
import zope.interface


@zope.interface.implementer(zeit.connector.interfaces.ICachingConnector)
class Connector(object):
    def __init__(self, roots={}, prefix=u'http://xml.zeit.de/'):
        roots.setdefault('postgresql', 'vivi')
        self._roots = roots

    def __getitem__(self, id):
        pass

    @classmethod
    def factory(cls):
        import zope.app.appsetup.product
        config = zope.app.appsetup.product.getProductConfiguration(
            'zeit.connector')
        return cls({
            'default': config['document-store'],
            'search': config['document-store-search']})


class TransactionBoundCachingConnector(Connector):
    pass


def connectorFactory():
    """Factory for creating the connector with data from zope.conf."""
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
