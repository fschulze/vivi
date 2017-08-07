from setuptools import setup, find_packages


setup(
    name='zeit.content.volume',
    version='1.8.0',
    author='gocept, Zeit Online',
    author_email='zon-backend@zeit.de',
    url='http://www.zeit.de/',
    description="vivi Content-Type Volume",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    license='BSD',
    namespace_packages=['zeit', 'zeit.content'],
    install_requires=[
        'gocept.form',
        'grokcore.component',
        'lxml',
        'pytz',
        'setuptools',
        'zc.sourcefactory',
        'zeit.cms >= 2.107.0.dev0',
        'zeit.content.article >= 3.23.0.dev0',
        'zeit.content.cp',
        'zeit.content.image',
        'zeit.content.text>=2.1.0.dev0',
        'zeit.solr',
        'zope.browserpage',
        'zope.component',
        'zope.formlib',
        'zope.interface',
        'zope.schema',
        'zope.security',
        'zope.traversing',
    ],
    entry_points={
        'fanstatic.libraries': [
            'zeit_content_volume=zeit.content.volume.browser.resources:lib',
        ],
    },
)
