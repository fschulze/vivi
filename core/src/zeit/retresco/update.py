from zeit.cms.content.sources import FEATURE_TOGGLES
from zeit.cms.repository.interfaces import ICollection, INonRecursiveCollection
from zeit.retresco.interfaces import ISkipEnrich
import argparse
import gocept.runner
import grokcore.component as grok
import logging
import six
import time
import transaction
import zeit.cms.celery
import zeit.cms.checkout.interfaces
import zeit.cms.content.interfaces
import zeit.cms.interfaces
import zeit.cms.repository.interfaces
import zeit.cms.workflow.interfaces
import zeit.cms.workingcopy.interfaces
import zeit.content.image.imagegroup
import zeit.content.image.transform
import zeit.retresco.interfaces
import zope.component
import zope.lifecycleevent


log = logging.getLogger(__name__)


@grok.subscribe(zope.lifecycleevent.IObjectMovedEvent)
def index_after_add(event):
    # We don't use the "extended" (object, event) method, as we are not
    # interested in the events which are dispatched to sublocations.
    context = event.object
    if zope.lifecycleevent.IObjectRemovedEvent.providedBy(event):
        return
    if not zeit.cms.interfaces.ICMSContent.providedBy(context):
        return
    if zeit.cms.repository.interfaces.IRepository.providedBy(context):
        return
    if zeit.cms.workingcopy.interfaces.IWorkingcopy.providedBy(
            event.newParent):
        return
    log.info('AfterAdd: Creating async index job for %s' % context.uniqueId)
    index_async.delay(context.uniqueId)


@grok.subscribe(
    zeit.cms.interfaces.ICMSContent,
    zeit.cms.checkout.interfaces.IAfterCheckinEvent)
def index_after_checkin(context, event):
    if event.publishing:
        return
    # XXX Work around race condition between celery/redis (applies already
    # in tpc_vote) and DAV-cache in ZODB (applies only in tpc_finish, so
    # the celery job *may* start executing before that happens), BUG-796.
    index_async.apply_async((context.uniqueId,), countdown=5)


@grok.subscribe(
    zeit.cms.interfaces.ICMSContent,
    zeit.cms.workflow.interfaces.IBeforePublishEvent)
def index_on_publish(context, event):
    # Unfortunately we have to enrich here too, even though strictly
    # speaking that "already happened" on checkin, to support the "checkin
    # and publish immediately" use case -- since there publish likely
    # happens *before* the index_async job created by checkin ran.
    enrich = True
    if not FEATURE_TOGGLES.find('tms_enrich_on_checkin'):
        enrich = False
    index(context, enrich=enrich)


@grok.subscribe(
    zeit.cms.interfaces.ICMSContent,
    zeit.cms.workflow.interfaces.IRetractedEvent)
def index_after_retract(context, event):
    index_async.apply_async((context.uniqueId, False), countdown=5)


@grok.subscribe(
    zeit.cms.interfaces.ICMSContent,
    zope.lifecycleevent.IObjectRemovedEvent)
def unindex_on_remove(context, event):
    if zeit.cms.workingcopy.interfaces.IWorkingcopy.providedBy(
            event.oldParent):
        return
    unindex_async.delay(zeit.cms.content.interfaces.IUUID(context).id)


@zeit.cms.celery.task(bind=True, queuename='search')
def index_async(self, uniqueId, enrich=True):
    context = zeit.cms.interfaces.ICMSContent(uniqueId, None)
    if context is None:
        log.warning('Could not index %s because it does not exist any longer.',
                    uniqueId)
        return
    if not FEATURE_TOGGLES.find('tms_enrich_on_checkin'):
        enrich = False
    meta = zeit.cms.content.interfaces.ICommonMetadata(context, None)
    has_keywords = meta is not None and meta.keywords
    try:
        index(
            context,
            enrich=enrich,
            update_keywords=enrich and not has_keywords)
    except zeit.retresco.interfaces.TechnicalError:
        self.retry()


def index(content, enrich=False, update_keywords=False, publish=False):
    if update_keywords and not enrich:
        raise ValueError('enrich is required for update_keywords')
    conn = zope.component.getUtility(zeit.retresco.interfaces.ITMS)
    stack = [content]
    errors = []
    while stack:
        content = stack.pop(0)
        if (ICollection.providedBy(content) and
                not INonRecursiveCollection.providedBy(content)):
            stack.extend(content.values())
        if should_skip(content):
            continue
        uuid = getattr(zeit.cms.content.interfaces.IUUID(content, None), 'id',
                       '<no-uuid>')
        log.info('Updating: %s %s, enrich: %s, keywords: %s, publish: %s',
                 content.uniqueId, uuid, enrich, update_keywords, publish)
        try:
            if enrich and not ISkipEnrich.providedBy(content):
                log.debug('Enriching: %s', content.uniqueId)
                response = conn.enrich(content)
                body = response.get('body')
                if update_keywords:
                    tagger = zeit.retresco.tagger.Tagger(content)
                    tagger.update(conn.generate_keyword_list(response),
                                  clear_disabled=False)
            else:
                # For reindex-only, preserve the previously enriched body.
                body = conn.get_article_data(content).get('body')

            conn.index(content, body)

            if publish:
                pub_info = zeit.cms.workflow.interfaces.IPublishInfo(content)
                if pub_info.published:
                    if zeit.retresco.interfaces.ITMSRepresentation(
                            content)() is not None:
                        log.info('Publishing: %s', content.uniqueId)
                        conn.publish(content)
                    else:
                        log.info(
                            'Skip publish for %s, missing required fields',
                            content.uniqueId)
        except zeit.retresco.interfaces.TechnicalError as e:
            log.info('Retrying %s due to %r', content.uniqueId, e)
            raise
        except Exception as e:
            errors.append(e)
            log.warning('Error indexing %s, giving up',
                        content.uniqueId, exc_info=True)
            continue
    return errors


@zeit.cms.celery.task(bind=True, queuename='search')
def unindex_async(self, uuid):
    conn = zope.component.getUtility(zeit.retresco.interfaces.ITMS)
    try:
        conn.delete_id(uuid)
    except zeit.retresco.interfaces.TechnicalError:
        self.retry()


# Mostly relevant for bulk reindex, since zeit.content.quiz is not used anymore
SKIP_TYPES = ['quiz']
THUMBNAIL_NAMES = [
    '/%s/' % zeit.content.image.transform.THUMBNAIL_FOLDER_NAME,
    zeit.content.image.imagegroup.Thumbnails.SOURCE_IMAGE_PREFIX,
]


def should_skip(content):
    for name in THUMBNAIL_NAMES:
        if name in content.uniqueId:
            log.debug('Skipping thumbnail %s', content)
            return True
    content_type = zeit.cms.type.get_type(content)
    if content_type in SKIP_TYPES:
        log.debug('Skipping %s due to its content type %s',
                  content, content_type)
        return True
    return False


@zeit.cms.celery.task(bind=True, queuename='manual')
def index_parallel(self, unique_id, enrich=False, publish=False):
    try:
        content = zeit.cms.interfaces.ICMSContent(unique_id)
    except TypeError:
        log.warning('Could not resolve %s, giving up', unique_id)
        return
    except Exception:
        self.retry()
    if (ICollection.providedBy(content) and
            not INonRecursiveCollection.providedBy(content)):
        children = content.values()
        for item in children:
            if should_skip(item):
                continue
            index_parallel.delay(item.uniqueId, enrich=enrich, publish=publish)
    else:
        if should_skip(content):
            return
        start = time.time()
        try:
            errors = index(content, enrich=enrich, update_keywords=enrich,
                           publish=publish)
        except zeit.retresco.interfaces.TechnicalError:
            self.retry()
        else:
            stop = time.time()
            if not errors:
                log.info('Processed %s in %s', content.uniqueId, stop - start)


@gocept.runner.once(principal=gocept.runner.from_config(
    'zeit.retresco', 'index-principal'))
def reindex():
    parser = argparse.ArgumentParser(description='Reindex folder in TMS')
    parser.add_argument(
        'ids', type=six.text_type, nargs='+', help='uniqueIds to reindex')
    parser.add_argument(
        '--file', action='store_true',
        help='Load uniqueIds from a file to reindex')
    parser.add_argument(
        '--parallel', action='store_true',
        help='process via job queue instead of directly')
    parser.add_argument(
        '--enrich', action='store_true',
        help='Perform TMS analyze/enrich prior to indexing')
    parser.add_argument(
        '--publish', action='store_true',
        help='Perform TMS publish after indexing')

    args = parser.parse_args()
    ids = args.ids
    if args.file:
        if len(args.ids) > 1:
            raise Exception("Only one file can be passed!")
        with open(args.ids[0], 'r') as f:
            ids = f.read().splitlines()

    for i, id in enumerate(ids):
        if args.parallel:
            index_parallel.delay(id, args.enrich, args.publish)
            if i % 10000 == 0:
                transaction.commit()
        else:
            index(
                zeit.cms.interfaces.ICMSContent(id),
                enrich=args.enrich, update_keywords=args.enrich,
                publish=args.publish)
