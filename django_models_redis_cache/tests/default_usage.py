"""
    You can set this part in your project settings.py
"""

from django_models_redis_cache.core import *


def get_connection_pool():
    host = 'localhost'
    port = 6379
    db = 0
    connection_pool = redis.ConnectionPool(
        decode_responses=True,
        host=host,
        port=port,
        db=db,
    )
    return connection_pool


REDIS_ROOTS = {
    'test_caching_root': RedisRoot(
        prefix='test_caching',
        connection_pool=get_connection_pool(),
        ignore_deserialization_errors=True,
        economy=True
    )
}

"""
    Default usage
    
    You can just copy it to:
        app/management/commands/command_name.py
    And just run with:
        python manage.py command_name
    Help:
        https://docs.djangoproject.com/en/3.2/howto/custom-management-commands/
        https://stackoverflow.com/a/14617309
"""

if redis_roots:
    if type(redis_roots) == dict:
        some_caching_redis_root = redis_roots['test_caching_root']
        some_caching_redis_root.register_django_models({
            DjangoModelToCache1: {
                'enabled': True,
                'ttl': 60 * 5,  # Cache every 5 mins
                'prefix': f'test_caching_root-DjangoModelToCache1-cache', # please make it unique
            },
            # DjangoModelToCache2: {
            #     'enabled': True,
            #     'ttl': 60 * 10,  # Cache every 10 mins
            #     'prefix': f'test_caching_root-DjangoModelToCache2-cache', # please make it unique
            # },
            # ...
        })
        # another_caching_redis_root = redis_roots['another_test_caching_root']
        # some_caching_redis_root.registered_django_models({...})
        roots_to_cache = [
            some_caching_redis_root,
            # another_caching_redis_root
        ]
        print('STARTING CACHING')
        while True:
            for redis_root in roots_to_cache:
                redis_root.check_cache()
    else:
        raise Exception('redis_roots must be dict')
else:
    raise Exception('No redis_roots')
