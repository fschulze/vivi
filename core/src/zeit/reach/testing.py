import zeit.cms.testing
import zeit.retresco.testing


product_config = """
<product-config zeit.reach>
    url http://localhost:{port}
    freeze-now
</product-config>
"""

HTTP_LAYER = zeit.cms.testing.HTTPLayer(
    zeit.cms.testing.RecordingRequestHandler,
    name='HTTPLayer', module=__name__)
CONFIG_LAYER = zeit.retresco.testing.ProductConfigLayer(
    product_config, package='zeit.reach', bases=(
        HTTP_LAYER,
        zeit.cms.testing.CONFIG_LAYER,))
ZCML_LAYER = zeit.cms.testing.ZCMLLayer(bases=(CONFIG_LAYER,))
ZOPE_LAYER = zeit.cms.testing.ZopeLayer(bases=(ZCML_LAYER,))


class FunctionalTestCase(zeit.cms.testing.FunctionalTestCase):

    layer = ZOPE_LAYER
