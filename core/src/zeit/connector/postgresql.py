from io import BytesIO
from lazy import lazy
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import LargeBinary
from sqlalchemy import Unicode
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import register
import datetime
import six
import zeit.connector.interfaces
import zeit.connector.resource
import zope.interface


RESOURCE_TYPE_PROPERTY = zeit.connector.interfaces.RESOURCE_TYPE_PROPERTY
RFC3339_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# engine = create_engine("postgresql:///vivi", echo=True, echo_pool=True, future=True)
engine = create_engine("postgresql:///vivi", echo_pool=True, future=True)
# engine = create_engine("postgresql:///vivi", future=True)

DBSession = scoped_session(sessionmaker(bind=engine))
register(DBSession)


metadata_object = MetaData()

BaseObject = declarative_base(metadata=metadata_object)


class StorageItem(BaseObject):
    __tablename__ = "storage"

    path = Column(Unicode, primary_key=True)
    blob = Column(LargeBinary, nullable=False)
    properties = Column(JSONB, nullable=False)


def _get_resource_type(properties):
    __traceback_info__ = (id, )
    r_type = properties.get(RESOURCE_TYPE_PROPERTY)
    if r_type is None:
        dav_type = properties.get(('resourcetype', 'DAV:'), '')
        content_type = properties.get(('getcontenttype', 'DAV:'), '')
        __traceback_info__ = (id, dav_type, content_type)
        if dav_type and 'collection' in dav_type:
            r_type = 'collection'
        elif content_type.startswith('image/'):
            r_type = 'image'
        else:
            r_type = 'unknown'
    return r_type


@zope.interface.implementer(zeit.connector.interfaces.ICachingConnector)
class Connector(object):
    def __init__(self, roots={}, prefix=u'http://xml.zeit.de/'):
        print("postgresql.Connector.__init__", roots, prefix)
        roots.setdefault('postgresql', 'vivi')
        self._roots = roots
        self._prefix = prefix
        metadata_object.create_all(engine)

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
        wdc = self._webdav_connector
        session = DBSession()
        item = session.get(StorageItem, path)
        if item is None:
            try:
                properties = wdc._get_resource_properties(cid)
            except (zeit.connector.dav.interfaces.DAVNotFoundError,
                    zeit.connector.dav.interfaces.DAVBadRequestError):
                print(cid, "Not found")
                raise KeyError(
                    "The resource %r does not exist." % six.text_type(cid))
            # properties have tuples of the form (key, namespace) as keys,
            # which doesn't work as json, so create a nested dict instead
            metadata = {}
            for (k, ns), v in properties.items():
                if isinstance(v, datetime.datetime):
                    v = v.strftime(RFC3339_FORMAT)
                metadata.setdefault(ns, {})[k] = v
            body = wdc._get_resource_body(cid)
            session.add(StorageItem(
                path=path,
                blob=body.read(),
                properties=metadata))
            result = wdc[id]
            print("DAV", id, result)
        else:
            # properties have tuples of the form (key, namespace) as keys,
            # which doesn't work as json, so we transform from a nested dict
            properties = {}
            for ns, d in item.properties.items():
                for k, v in d.items():
                    properties[(k, ns)] = v
            resource_type = _get_resource_type(properties)
            content_type = properties.get(('getcontenttype', 'DAV:'))
            body = BytesIO(item.blob)
            del item
            result = zeit.connector.resource.CachedResource(
                six.text_type(cid), wdc._id_splitlast(cid)[1].rstrip('/'),
                resource_type,
                lambda: properties,
                lambda: body,
                content_type=content_type)
            print("DB", path, result)
        return result

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
