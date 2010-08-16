# Copyright (c) 2009 gocept gmbh & co. kg
# See also LICENSE.txt

from setuptools import setup, find_packages


setup(
    name='zeit.content.cp',
    version='0.42.0',
    author='gocept',
    author_email='mail@gocept.com',
    url='https://intra.gocept.com/projects/projects/zeit-cms',
    description="""\
""",
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    zip_safe=False,
    license='gocept proprietary',
    namespace_packages = ['zeit', 'zeit.content'],
    install_requires=[
        'feedparser',
        'gocept.cache',
        'gocept.lxml',
        'gocept.mochikit>=1.4.2.2',
        'gocept.runner>-0.4',
        'gocept.selenium>=0.6',
        'lxml',
        'python-cjson',
        'setuptools',
        'simplejson',
        'stabledict',
        'zc.sourcefactory',
        'zeit.brightcove>=0.3.0',
        'zeit.cms>1.44.0',
        'zeit.content.quiz>=0.4.2',
        'zeit.find >= 0.4',
        'zeit.solr',
        'zope.app.appsetup',
        'zope.app.pagetemplate',
        'zope.component',
        'zope.container>=3.8.1',
        'zope.event',
        'zope.formlib',
        'zope.i18n',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.viewlet',
    ],
    entry_points = """
        [console_scripts]
        refresh-feeds = zeit.content.cp.feed:refresh_all
        sweep-teasergroup-repository = zeit.content.cp.teasergroup.teasergroup:sweep_repository
    """,
)
