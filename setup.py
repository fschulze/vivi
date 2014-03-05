from setuptools import setup, find_packages

setup(
    name='zeit.securitypolicy',
    version='2.1.2.dev0',
    author='gocept',
    author_email='mail@gocept.com',
    url='https://code.gocept.com/hg/public/zeit.securitypolicy',
    description="""\
""",
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    zip_safe=False,
    license='gocept proprietary',
    namespace_packages = ['zeit'],
    install_requires=[
        'setuptools',
        'xlrd',
        'zeit.brightcove',
        'zeit.calendar',
        'zeit.cms>=2.15.0.dev0',
        'zeit.content.article',
        'zeit.content.image>=2.0.0.dev0',
        'zeit.content.link',
        'zeit.content.quiz',
        'zeit.content.rawxml',
        'zeit.content.video',
        'zeit.imp',
        'zeit.invalidate',
        'zeit.seo',
        'zope.app.zcmlfiles',
    ],
)
