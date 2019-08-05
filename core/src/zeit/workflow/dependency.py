import grokcore.component as grok
import zeit.cms.interfaces
import zeit.workflow.interfaces
import zope.component


@grok.implementer(zeit.workflow.interfaces.IPublicationDependencies)
class Dependencies(grok.Adapter):
    """Adapter to find the publication dependencies of an object."""

    grok.context(zeit.cms.interfaces.ICMSContent)

    def get_dependencies(self):
        dependencies = set()
        for adapter in self._find_adapters():
            dependencies.update(adapter.get_dependencies())
        return sorted(dependencies, key=lambda x: x.uniqueId)

    def get_retract_dependencies(self):
        dependencies = set()
        for adapter in self._find_adapters():
            if adapter.retract_dependencies:
                dependencies.update(adapter.get_dependencies())
        return sorted(dependencies, key=lambda x: x.uniqueId)

    def _find_adapters(self):
        for name, adapter in zope.component.getAdapters(
                (self.context,),
                zeit.workflow.interfaces.IPublicationDependencies):
            if not name:
                # This is actually this adapter
                continue
            yield adapter


@grok.implementer(zeit.workflow.interfaces.IPublicationDependencies)
class DependencyBase(grok.Adapter):

    grok.name('must be set in subclass')
    grok.baseclass()

    retract_dependencies = False

    def get_dependencies(self):
        return ()
