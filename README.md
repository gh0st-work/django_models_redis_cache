# django-models-redis-cache

## **Django Models Redis Cache (DMoReCa), library that gives your specified Django models regular caching via Redis**

For one project, I needed to work with redis, but redis-py provides a minimum level of work with redis. I didn't find any Django-like ORM for redis, so I wrote library [python-redis-orm](https://github.com/gh0st-work/python_redis_orm/) ([PyPI](https://pypi.org/project/python-redis-orm/)).

Also, if you are searching for just django-like redis ORM, please check [django-redis-orm](https://github.com/gh0st-work/django_redis_orm/) ([PyPI](https://pypi.org/project/django-redis-orm/)).

**And this library is port to Django that provides easy-to-use Django models caching via Redis**.

### Working with this library, you are expected:

- Fully works in 2021
- Saving almost all types of fields automatically
- Efficient data storage (SET model_name:instance_id "JSON string")
- Async caching
- Connection pooling
- Easy adaptation to your needs
- Adequate informational messages and error messages
- Built-in RedisRoot class that stores specified models, with:
    - **prefix** setting - prefix of this RedisRoot to be stored in redis
    - **connection_pool** setting - your redis.ConnectionPool instance (from redis-py)
    - **async_db_requests_limit** setting - your database connections limit
    - **ignore_deserialization_errors** setting - do not raise errors, while deserializing data
    - **save_consistency** setting - show structure-first data
    - **economy** setting - to not return full data and save some requests (usually, speeds up your app on 80%)
- Customizing caching settings by model:
    - **enabled** setting - to cache or not
    - **ttl** setting - cache period
    - **save_related_models** setting - save ForeignKey-s and ManyToMany-s instances
    - **exclude_fields** setting - field names to be excluded from caching
    - **filter_by** - setting - only models that passed filter params will be cached
- CRUD (Create Read Update Delete), in our variation: save, get, filter, order, update, delete:
    - `example_instance = ExampleModel(example_field='example_data').save()` - to create an instance and get its data dict
    - `filtered_example_instances = redis_root.get(ExampleModel, example_field='example_data')` - to get all ExampleModel instances with example_field filter and get its data dict
    - `ordered_instances = redis_root.order(filtered_example_instances, '-id')` - to get ordered filtered_example_instances by id ('-' for reverse)
    - `updated_example_instances = redis_root.update(ExampleModel, ordered_instances, example_field='another_example_data')` - to update all ordered_instances example_field with value 'another_example_data' and get its data dict
    - `redis_root.delete(ExampleModel, updated_example_instances)` - to delete updated_example_instances

# Installation
`pip install django-models-redis-cache`

[Here is PyPI](https://pypi.org/project/django-models-redis-cache/)

Add "django_models_redis_cache" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'django_models_redis_cache',
    ]

# Usage

1. Create **RedisRoot** with params:
    - **prefix** - (str) prefix for your redis root
    - **connection_pool** - (redis.ConnectionPool) redis-py redis.ConnectionPool instance, with decode_responses=True
    - **async_db_requests_limit** - (int) your database has max connections limit, please enter it here
    - **ignore_deserialization_errors** - (bool) to ignore deserialization errors or raise exception
    - **economy** - (bool) if True, all create/update requests will return only instance id 
2. Call **register_django_models({...})** on your RedisRoot instance and provide dict, where keys are django models and values are dicts (django_model:dict) with config params (str:value):
    - **enabled** - (bool) - to cache or not
    - **ttl** - (int) - to cache every x seconds
    - **save_related_models** - (bool) - to save ForeignKey-s and ManyToMany-s instances or not
    - **exclude_fields** - (list of strings) - fields to exclude from caching
    - **filter_by** - (dict str:value) - filter objects to cache by something
3. Call **check_cache()** on your RedisRoot instance

# Example usage

### Settings

You can set this part in your project settings.py:

```python
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

```

### Run in the background

You can just copy it to:

`app/management/commands/command_name.py`
    
And just run with:

`python manage.py command_name`
    
Help:

[Django custom management commands](https://docs.djangoproject.com/en/3.2/howto/custom-management-commands/)
    
[How to import something from settings](https://stackoverflow.com/a/14617309)

```python

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

```

