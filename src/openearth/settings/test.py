from dev import *

FILER_STORAGES = {
    'private': {
        'main': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': '/tmp/smedia/files',
                'base_url': '/smedia/',
            },
            'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
        },
        'thumbnails': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': '/tmp/smedia/files/files_thumbnails',
                'base_url': '/smedia/files_thumbnails/',
            },
        },
    },
}