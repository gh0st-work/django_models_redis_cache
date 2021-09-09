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
        async_db_requests_limit=100,
        ignore_deserialization_errors=True,
        save_consistency=False,
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

redis_roots = getattr(settings, "REDIS_ROOTS", None)
if redis_roots:
    if type(redis_roots) == dict:
        test_caching_root = redis_roots['test_caching_root']
        test_caching_root.register_django_models({
            CustomUser: {
                'enabled': True,
                'ttl': 60 * 15,
                'save_related_models': True,
                'exclude_fields': [
                    'is_admin',
                    'api_key',
                    'first_name',
                    'last_name',
                    'email',
                    'is_staff',
                    'date_joined',
                    'password',
                    'last_login',
                    'user_permissions',
                    'is_superuser',
                    'groups',
                ],
            },
            BotSoft: {
                'enabled': True,
                'ttl': 60 * 15,
                'save_related_models': True,
                'exclude_fields': [
                    'name',
                    'image',
                    'image_webp',
                    'developer_url'
                ],
            },
            Service: {
                'enabled': True,
                'ttl': 60 * 15,
                'save_related_models': True,
                'exclude_fields': [
                    'name_append',
                    'description',
                    'min',
                    'max',
                ],
            },
            CustomService: {
                'enabled': True,
                'ttl': 60 * 15,
                'save_related_models': True,
                'exclude_fields': [
                    'name_append',
                ],
            },
            UniqueTask: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
            },
            Task: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': False,
                'filter_by': {
                    'status': 'in_work',
                }
            },
            Account: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
                'filter_by': {
                    'last_task_completed_in__gte': datetime.datetime.now() - datetime.timedelta(days=14),
                    'last_checked_in__gte': datetime.datetime.now() - datetime.timedelta(days=14),
                }
            },
            BotSession: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
            },
            TaskChallenge: {
                'enabled': True,
                'ttl': 60 * 1,
                'save_related_models': True,
            },
        })
        roots_to_cache = [
            test_caching_root,
        ]
        print('STARTING CACHING')
        while True:
            for redis_root in roots_to_cache:
                redis_root.check_cache()
    else:
        raise Exception('redis_roots must be dict')
else:
    raise Exception('No redis_roots')
