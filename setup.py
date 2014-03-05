from setuptools import setup, find_packages

setup(
    name='zeit.wysiwyg',
    version='2.0.3.dev0',
    author='gocept',
    author_email='mail@gocept.com',
    url='https://svn.gocept.com/repos/gocept-int/zeit.cms',
    description="ZEIT WYSIWYG Editor integration",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    license='gocept proprietary',
    namespace_packages=['zeit'],
    install_requires=[
        'gocept.fckeditor[fanstatic]>=2.6.4.1-2',
        'lxml',
        'pytz',
        'rwproperty',
        'setuptools',
        'zc.iso8601',
        'zc.resourcelibrary',
        'zeit.cms>=2.15.0.dev0',
        'zeit.content.image',
        'zope.app.pagetemplate',
        'zope.app.testing',
        'zope.cachedescriptors',
        'zope.component',
        'zope.formlib',
        'zope.interface',
        'zope.security',
        'zope.testing',
        'zope.traversing',
    ],
    extras_require=dict(test=[
        'zeit.content.gallery',
        'zeit.content.infobox',
        'zeit.content.portraitbox',
    ]),
    entry_points={
        'fanstatic.libraries': [
            'zeit_wysiwyg=zeit.wysiwyg.browser.resources:lib',
        ],
    },
)
