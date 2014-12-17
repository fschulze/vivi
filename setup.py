from setuptools import setup, find_packages

setup(
    name='zeit.content.image',
    version='2.2.6',
    author='gocept',
    author_email='mail@gocept.com',
    url='https://bitbucket.org/gocept/zeit.content.image',
    description="ZEIT Image",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    license='gocept proprietary',
    namespace_packages=['zeit', 'zeit.content'],
    install_requires=[
        'ZODB',
        'Pillow',
        'gocept.async',
        'gocept.form',
        'gocept.httpserverlayer',
        'gocept.selenium',
        'grokcore.component',
        'lxml',
        'persistent',
        'pytz',
        'setuptools',
        'transaction',
        'z3c.conditionalviews',
        'zc.form',
        'zc.sourcefactory',
        'zc.table',
        'zeit.cms>=2.31.0.dev0',
        'zeit.connector>=2.4.0.dev0',
        'zeit.edit>=2.1.7.dev0',
        'zeit.imp>=0.15.0.dev0',
        'zeit.wysiwyg',
        'zope.app.appsetup',
        'zope.app.container',
        'zope.app.file',
        'zope.app.generations',
        'zope.app.pagetemplate',
        'zope.browserpage',
        'zope.cachedescriptors',
        'zope.component',
        'zope.file',
        'zope.formlib',
        'zope.interface',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.testbrowser',
        'zope.testing',
    ],
    entry_points={
        'fanstatic.libraries': [
            'zeit_content_image=zeit.content.image.browser.resources:lib',
        ],
    },
)
