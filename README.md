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
- Built-in RedisRoot class that stores specified models, with (optional):
    - Async database limit
    - Ignoring deserialization errors
    - Use structure-first data
- Customizing caching settings by model (optional):
    - Cache every X seconds
    - Save related models
    - Fields to exclude from caching
    - Filter objects to cache
- CRUD (Create Read Update Delete), that uses your django models

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
    - **prefix** (str) - prefix for your redis root
    - **connection_pool** (redis.ConnectionPool) - redis-py redis.ConnectionPool instance, with decode_responses=True
    - **async_db_requests_limit** (int) - your database has max connections limit, please enter it here
    - **ignore_deserialization_errors** (bool) - to ignore deserialization errors or raise exception
    - **economy** (bool) - if True, all update requests will return only instance id 
2. Call **register_django_models({...})** on your RedisRoot instance and provide dict, where keys are django models and values are dicts (django_model:dict) with config params (str:value):
    - **enabled** (bool) - to cache or not
    - **ttl** (int) - to cache every x seconds
    - **save_related_models** (bool) - to save ForeignKey-s and ManyToMany-s instances or not
    - **exclude_fields** (list of strings) - fields to exclude from caching
    - **filter_by** (dict str:value) - filter objects to cache by something
    - **delete** (bool) - foolproof
    - **write_to_django** (bool) - if you need to write data to django, also uses as foolproof
3. Call **check_cache()** on your RedisRoot instance
4. Use our CRUD, or just get your cached data

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
                'delete': True,
                'write_to_django': True,
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
                'delete': True,
                'write_to_django': True,
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
                'delete': True,
                'write_to_django': True,
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
                'delete': True,
                'write_to_django': True,
                'exclude_fields': [
                    'name_append',
                ],
            },
            UniqueTask: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
                'delete': True,
                'write_to_django': True,
            },
            Task: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
                'delete': True,
                'write_to_django': True,
                'filter_by': {
                    'status': 'in_work',
                }
            },
            Account: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
                'delete': True,
                'write_to_django': True,
                'filter_by': {
                    'last_task_completed_in__gte': datetime.datetime.now() - datetime.timedelta(days=14),
                    'last_checked_in__gte': datetime.datetime.now() - datetime.timedelta(days=14),
                }
            },
            BotSession: {
                'enabled': True,
                'ttl': 60 * 5,
                'save_related_models': True,
                'delete': True,
                'write_to_django': True,
            },
            TaskChallenge: {
                'enabled': True,
                'ttl': 60 * 1,
                'save_related_models': True,
                'delete': True,
                'write_to_django': True,
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


### Use in views

If you enabled write_to_django and delete, you can fully use redis caching and does not care about writing to the database with 

**our CRUD**:

```python

    # Django part
    gh0st_user = CustomUser.objects.get(username='gh0st')
    another_user = CustomUser.objects.get(username='another_username')
    random_service = random.choice(list(Service.objects.all()))
    placement = random_service.placement
    if ServiceCustomPrice.objects.filter(user=gh0st_user, service=random_service, active=True):
        placement = ServiceCustomPrice.objects.get(user=gh0st_user, service=random_service, active=True).price
    if gh0st_user.sale:
        placement = placement * gh0st_user.sale
    task_count = 9999
    task_price = task_count * placement
    new_task_1_params = {
        'owner': gh0st_user,
        'service': random_service,
        'url': 'https://github.com/gh0st-work/',
        'count': task_count,
        'price': task_price,
        'status': 'checking',
    }
    new_task_1 = Task.objects.create(**new_task_1_params)
    new_task_2_params = {
        'owner': another_user,
        'service': random_service,
        'url': 'https://github.com/gh0st-work/',
        'count': task_count,
        'price': task_price,
        'status': 'checking',
    }
    new_task_2 = Task.objects.create(**new_task_2_params)
    
    
    
    # Cache part
    # Preparations
    test_caching_root.check_cache()  # Just for testing, if it not runned in the background and not caching right now
    
    # Get
    cached_task_1 = test_caching_root.get(Task, django_id=new_task_1.id)  # filter by django_id, if you leave blank will return all instances
    print('\n\n\n')
    cached_task_2 = test_caching_root.get(Task, django_id=new_task_2.id)  # filter by django_id, if you leave blank will return all instances
    success = False
    try:
        cached_task_1 = cached_task_1[0]
        cached_task_2 = cached_task_2[0]
        if cached_task_1['owner']['django_id'] == new_task_1.owner.id:
            if cached_task_1['price'] == new_task_1.price:
                if cached_task_2['owner']['django_id'] == new_task_2.owner.id:
                    if cached_task_2['price'] == new_task_2.price:
                        success = True
    except:
        pass
    print(f'Get test: {success = }')  # If create works, will print: "Get test: success = True"

    # Create and deep filtering
    new_task_params = new_task_1_params
    new_task_params['owner'] = test_caching_root.get(CustomUser, username='gh0st')
    new_task_params['service'] = test_caching_root.get(Service, django_id=random_service.id)
    created_task = test_caching_root.create(Task, **new_task_params)
    cached_gh0st_tasks = test_caching_root.get(Task, owner__username='gh0st')
    all_tasks_owner_is_gh0st = all([
        (task['owner']['username'] == 'gh0st')
        for task in cached_gh0st_tasks
    ])
    task_created = (created_task in cached_gh0st_tasks)
    success = (all_tasks_owner_is_gh0st and task_created)
    print(f'Create and deep filtering test: {success = }')  # If works, will print: "Create and deep filtering test: success = True"

    # Update
    random_price_first_part = Decimal(random.randrange(0, 10000))
    random_price_second_part = Decimal(random.randrange(0, 1000))
    random_price = random_price_first_part + random_price_second_part / Decimal(1000)
    test_caching_root.update(
        Task, cached_task_2,
        price=random_price,
        status='completed',
    )
    cached_task_2 = test_caching_root.get(
        Task,
        price=random_price,  # filter by price, if you leave blank will return all instances
        status__in=['checking', 'completed'],  # if status in the list
    )
    success = False
    try:
        cached_task_2 = cached_task_2[0]
        price_is_same = (cached_task_2['price'] == random_price)
        django_id_is_same = (cached_task_2['django_id'] == new_task_2.id)
        status_is_completed = (cached_task_2['status'] == 'completed')
        if price_is_same and django_id_is_same and status_is_completed:
            success = True
    except:
        pass
    print(f'Update test: {success = }')  # If works, will print: "Update test: success = True"

    # Delete
    test_caching_root.delete(Task, cached_task_2)
    old_cached_task_2 = test_caching_root.get(Task, price=random_price)
    success = (not len(old_cached_task_2))
    print(f'Delete test: {success = }')  # If works, will print: "Delete test: success = True"


```
