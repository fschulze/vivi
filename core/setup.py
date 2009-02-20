from setuptools import setup, find_packages

setup(
    name='zeit.imp',
    version='0.5dev',
    author='gocept',
    author_email='mail@gocept.com',
    url='https://svn.gocept.com/repos/gocept-int/zeit.cms/zeit.imp',
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
        'webcolors',
        'zeit.cms>=1.10.2',
        'zc.selenium',
    ],
)
