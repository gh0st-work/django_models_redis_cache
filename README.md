# django-models-redis-cache

## **Django Models Redis Cache, library that gives your specified django models regular caching via redis**

For one project, I needed to work with redis, but redis-py provides a minimum level of work with redis. I didn't find any Django-like ORM for redis, so I wrote library [python-redis-orm](https://github.com/gh0st-work/python_redis_orm/) ([PyPI](https://pypi.org/project/python-redis-orm/)).

And this library is port to Django that **provides easy-to-use Django models caching via Redis**.

### Working with this library, you are expected:

- Fully works in 2021
- Easy adaptation to your needs
- Adequate informational messages and error messages
- Built-in RedisRoot class that stores specified models, with:
    - **redis_instance** setting - your redis connection (from redis-py)
    - **prefix** setting - prefix of this RedisRoot to be stored in redis
    - **ignore_deserialization_errors** setting - do not raise errors, while deserealizing data
    - **save_consistency** setting - show structure-first data
    - **economy** setting - to not return full data and save some requests (usually, speeds up your app on 80%)
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

### You can set this part in your project settings.py

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
        ignore_deserialization_errors=True,
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

if redis_roots:
    if type(redis_roots) == dict:
        some_caching_redis_root = redis_roots['test_caching_root']
        some_caching_redis_root.registered_django_models({
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
    raise Exception('No REDIS_ROOTS')

```

