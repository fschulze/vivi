from io import BytesIO
from lazy import lazy
from lxml.html import fromstring as parse_html
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import LargeBinary
from sqlalchemy import Unicode
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapper
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
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
# engine = create_engine("postgresql:///vivi", echo=True, future=True)
engine = create_engine("postgresql:///vivi", echo_pool=True, future=True)
# engine = create_engine("postgresql:///vivi", future=True)

DBSession = scoped_session(sessionmaker(bind=engine))
register(DBSession)


def _index_object(session, instance):
    # store a "hard" reference to the object on the session,
    # otherwise gc will remove the instances from the weak identity_map
    # during the request, which would cause a re-fetch from the db
    # see https://github.com/sqlalchemy/sqlalchemy/discussions/7246
    set_ = session.info.get("strong_set", None)
    if not set_:
        session.info["strong_set"] = set_ = set()

    set_.add(instance)


@event.listens_for(Mapper, "load")
def object_loaded(instance, ctx):
    _index_object(ctx.session, instance)


@event.listens_for(DBSession, "after_attach")
def index_object(session, instance):
    _index_object(session, instance)


metadata_object = MetaData()

BaseObject = declarative_base(metadata=metadata_object)


class StorageItem(BaseObject):
    __tablename__ = "storage"

    path = Column(Unicode, primary_key=True)
    blob = Column(LargeBinary, nullable=False)
    properties = Column(JSONB, nullable=False)


class CanonicalPath(BaseObject):
    __tablename__ = "canonical_path"

    id = Column(Unicode, primary_key=True)
    path = Column(
        Unicode,
        ForeignKey(StorageItem.path, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True)
    item = relationship(StorageItem, lazy='joined')


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

    def _id2path(self, id):
        if not id.startswith(self._prefix):
            raise ValueError("Bad id %r (prefix is %r)" % (id, self._prefix))
        return id[len(self._prefix):]

    @lazy
    def DAVConnector(self):
        import zeit.connector.connector
        return zeit.connector.connector.Connector

    @lazy
    def _webdav_connector(self):
        print("postgresql.Connector._webdav_connector")
        connector = self.DAVConnector(self._roots, self._prefix)
        connector.from_postgresql = True
        return connector

    def _webdav_get(self, session, id):
        wdc = self._webdav_connector
        cid = self._webdav_connector._get_cannonical_id(id)
        path = self._id2path(cid)
        try:
            properties = wdc._get_resource_properties(cid)
        except (zeit.connector.dav.interfaces.DAVNotFoundError,
                zeit.connector.dav.interfaces.DAVBadRequestError):
            print(cid, "Not found")
            # cache not found
            session.add(CanonicalPath(id=id, path=None))
            raise KeyError(
                "The resource %r does not exist." % six.text_type(cid))
        # properties have tuples of the form (key, namespace) as keys,
        # which doesn't work as json, so create a nested dict instead
        metadata = {}
        for (k, ns), v in properties.items():
            if isinstance(v, datetime.datetime):
                if k == 'cached-time':
                    # ignore property from zeo cache
                    continue
                raise RuntimeError("datetime %r %r" % (k, v))
                v = v.strftime(RFC3339_FORMAT)
            metadata.setdefault(ns, {})[k] = v
        body = wdc._get_resource_body(cid)
        session.add(StorageItem(
            path=path,
            blob=body.read(),
            properties=metadata))
        session.add(CanonicalPath(id=cid, path=path))
        if id != cid:
            session.add(CanonicalPath(id=id, path=path))
        result = wdc[id]
        print("DAV", id, result)
        return result

    def _db_get(self, session, id):
        # properties have tuples of the form (key, namespace) as keys,
        # which doesn't work as json, so we transform from a nested dict
        cpath = session.get(CanonicalPath, id)
        if cpath is None:
            cid = self._webdav_connector._get_cannonical_id(id)
            cpath = session.get(CanonicalPath, cid)
            if cpath is None:
                return None
            session.add(CanonicalPath(id=id, path=cpath.item.path))
        if cpath.path is None:
            raise KeyError(
                "The resource %r does not exist." % six.text_type(id))
        item = cpath.item
        properties = {}
        for ns, d in item.properties.items():
            for k, v in d.items():
                # TODO handle conversion of datetime objects
                properties[(k, ns)] = v
        resource_type = _get_resource_type(properties)
        content_type = properties.get(('getcontenttype', 'DAV:'))
        body = BytesIO(item.blob)
        path = item.path
        cid = self._prefix + path
        result = zeit.connector.resource.CachedResource(
            six.text_type(cid),
            self.DAVConnector._id_splitlast(cid)[1].rstrip('/'),
            resource_type,
            lambda: properties,
            lambda: body,
            content_type=content_type)
        # print("DB", path, result)
        return result

    def __getitem__(self, id):
        session = DBSession()
        result = self._db_get(session, id)
        if result is None:
            result = self._webdav_get(session, id)
        return result

    def listCollection(self, id):
        body = self[id].data.read()
        tree = parse_html(body)
        result = sorted(
            (x.text.rstrip('/'), id + x.text)
            for x in tree.cssselect('td > a')
            if x.text != 'Parent Directory' and not x.attrib['href'].startswith('/'))
        _result = sorted(self._webdav_connector.listCollection(id))
        if result != _result:
            print("listCollection (differences)", id, set(result).symmetric_difference(_result))
            print(body)
            return _result
        # print("listCollection", id, result)
        return result

    def add(self, obj, verify_etag=True):
        result = self._webdav_connector.add(obj, verify_etag=verify_etag)
        print("add", obj, verify_etag, result)
        return result

    def lock(self, id, principal, until):
        result = self._webdav_connector.lock(id, principal, until)
        print("lock", id, principal, until, result)
        return result

    def locked(self, id):
        # return (None, None, False)
        return self._webdav_connector.locked(id)

    def unlock(self, id, locktoken=None, invalidate=True):
        result = self._webdav_connector.unlock(
            id, locktoken=locktoken, invalidate=invalidate)
        print("unlock", id, locktoken, invalidate, result)
        return result

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
