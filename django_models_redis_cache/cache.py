import asyncio
import datetime

from asgiref.sync import sync_to_async
from django.db import models as django_models


def default_cache_func(
        redis_root,
        django_model,
        cache_conf,
):
    django_to_cache(
        redis_root,
        django_model,
        cache_conf,
    )
    cache_to_django(
        redis_root,
        django_model,
        cache_conf,
    )


def cache_to_django(
        redis_root,
        django_model,
        cache_conf,
):
    async def run_cache_to_django(
            redis_root,
            django_model,
            cache_conf,
    ):
        redis_dicts = redis_root.get(django_model, return_dict=True)
        async_chunk_size = redis_root.async_db_requests_limit
        async_tasks = []
        completed = 0
        to_complete = len(redis_dicts.keys())

        for redis_instance_id, redis_instance_data in redis_dicts.items():
            async_tasks.append(
                update_or_create_django_instance_from_redis_instance(
                    redis_instance_data,
                    django_model,
                    cache_conf,
                )
            )
            completed += 1
            if len(async_tasks) == async_chunk_size or completed == to_complete:
                await asyncio.gather(*async_tasks)
                async_tasks = []
                print(
                    f'{datetime.datetime.now()} - '
                    f'Written {completed} {django_model} instances from cache to django')

        if cache_conf['delete']:

            async def check_if_need_to_delete_django_instance(redis_instances_django_ids, django_instance):
                if django_instance.id not in redis_instances_django_ids:
                    await django_sync_to_async_list(django_instance.delete)

            all_redis_instances = redis_root.get(django_model)
            redis_instances_django_ids = []
            for redis_instance in all_redis_instances:
                if 'django_id' in redis_instance.keys():
                    redis_instances_django_ids.append(redis_instance['django_id'])

            all_django_instances = await django_sync_to_async_list(django_model.objects.all)
            async_tasks = []
            completed = 0
            to_complete = len(all_django_instances)
            for django_instance in all_django_instances:
                async_tasks.append(
                    check_if_need_to_delete_django_instance(
                        redis_instances_django_ids,
                        django_instance,
                    )
                )
                completed += 1
                if len(async_tasks) == async_chunk_size or completed == to_complete:
                    await asyncio.gather(*async_tasks)
                    async_tasks = []
                    print(f'{datetime.datetime.now()} - '
                          f'Deleted {django_model} instances from django')

            await asyncio.gather(*async_tasks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cache_to_django(
        redis_root,
        django_model,
        cache_conf,
    ))


async def update_or_create_django_instance_from_redis_instance(
        redis_instance,
        django_model,
        cache_conf,
):
    django_id = redis_instance['django_id']
    django_params, django_many_to_many_params = await async_redis_dict_to_django_params(
        redis_instance,
        django_model,
        cache_conf,
    )
    new_django_params = {}
    for k, v in django_params.items():
        if k not in ['django_id', 'id']:
            new_django_params[k] = v
    django_params = new_django_params
    django_instance = await sync_to_async_update_or_create_django_instance_from_redis_instance(
        django_id,
        django_model,
        django_params,
        django_many_to_many_params,
        cache_conf,
    )

    return django_instance


@sync_to_async
def sync_to_async_update_or_create_django_instance_from_redis_instance(
        django_id,
        django_model,
        django_params,
        django_many_to_many_params,
        cache_conf,
):
    need_to_create = True
    if django_id not in ['null', None]:
        if django_model.objects.filter(id=django_id):
            need_to_create = False

    django_instance = None

    if need_to_create:
        if cache_conf['write_to_django']:
            django_instance = django_model.objects.create(**django_params)
            update_django_many_to_many(
                django_model,
                django_instance.id,
                django_many_to_many_params
            )
        else:
            print(f'\n'
                  f'{datetime.datetime.now()} - '
                  f'Setting write_to_django is turned off, need to write:\n'
                  f'Create {django_model} with params: \n'
                  f'{django_params}\n'
                  f'and many to many params\n'
                  f'{django_many_to_many_params}'
                  f'\n')
    else:
        django_instance = django_model.objects.filter(id=django_id)[0]
        changed_fields_to_update = {}
        for redis_field_name, redis_field_value in django_params.items():
            django_instance_fields_value = getattr(django_instance, redis_field_name)
            if django_instance_fields_value.__class__ == datetime.datetime:
                if redis_field_value.__class__ == datetime.datetime:
                    redis_field_value_formatted = redis_field_value.strftime('%Y.%m.%d-%H:%M:%S')
                    django_instance_fields_value_formatted = django_instance_fields_value.strftime('%Y.%m.%d-%H:%M:%S')
                    if redis_field_value_formatted != django_instance_fields_value_formatted:
                        changed_fields_to_update[redis_field_name] = redis_field_value
                else:
                    changed_fields_to_update[redis_field_name] = redis_field_value
            elif django_instance_fields_value != redis_field_value:
                changed_fields_to_update[redis_field_name] = redis_field_value
        changed_many_to_many_fields_to_update = {}
        for redis_field_name, redis_field_value in django_many_to_many_params.items():
            django_instance_fields_value = list(getattr(django_instance, redis_field_name).all())
            if django_instance_fields_value != redis_field_value:
                changed_many_to_many_fields_to_update[redis_field_name] = redis_field_value
        if cache_conf['write_to_django']:
            django_model.objects.filter(id=django_id).update(**changed_fields_to_update)
            update_django_many_to_many(
                django_model,
                django_id,
                changed_many_to_many_fields_to_update
            )
            django_instance = django_model.objects.filter(id=django_id)[0]
        else:
            print(f'\n'
                  f'{datetime.datetime.now()} - '
                  f'Setting write_to_django is turned off, need to write:\n'
                  f'Update {django_model} (ID {django_id}) with params: \n'
                  f'{changed_fields_to_update}\n'
                  f'and many to many params\n'
                  f'{changed_many_to_many_fields_to_update}'
                  f'\n')
    return django_instance


async def async_redis_dict_to_django_params(
        redis_dict,
        django_model,
        cache_conf,
):
    django_params = {}
    django_many_to_many_params = {}
    django_model_fields = await sync_to_async_get_model_fields(django_model)
    for django_field in django_model_fields:
        django_field_data = await sync_to_async_get_django_field_data(django_field)
        django_field_name = django_field_data['name']
        if django_field_name in redis_dict.keys():
            if django_field_data['class'] == django_models.ForeignKey:
                foreign_key_model = django_field_data['remote_field_model']
                redis_foreign_key_instance = redis_dict[django_field_name]
                if redis_foreign_key_instance not in ['null', None]:
                    django_foreign_key_instance = await update_or_create_django_instance_from_redis_instance(
                        redis_foreign_key_instance,
                        foreign_key_model,
                        cache_conf,
                    )
                    django_params[django_field_name] = django_foreign_key_instance
                else:
                    django_params[django_field_name] = None
            elif django_field_data['class'] == django_models.ManyToManyField:
                many_to_many_model = django_field_data['remote_field_model']
                django_many_to_many_instances = []
                redis_many_to_many_instances = redis_dict[django_field_data['name']]
                if redis_many_to_many_instances not in ['null', None] and redis_many_to_many_instances:
                    for redis_many_to_many_instance in redis_many_to_many_instances:
                        django_many_to_many_instance = await update_or_create_django_instance_from_redis_instance(
                            redis_many_to_many_instance,
                            many_to_many_model,
                            cache_conf,
                        )
                        django_many_to_many_instances.append(django_many_to_many_instance)
                django_many_to_many_params[django_field_name] = django_many_to_many_instances
            else:
                value = redis_dict[django_field_data['name']]
                django_params[django_field_name] = value

    return django_params, django_many_to_many_params


@sync_to_async
def sync_to_async_get_model_fields(django_model):
    return list(django_model._meta.get_fields())


@sync_to_async
def sync_to_async_get_django_field_data(django_field):
    django_field_data = {
        'name': django_field.name,
        'class': django_field.__class__,
        'remote_field_model': None,
    }
    try:
        django_field_data['remote_field_model'] = django_field.remote_field.model
    except:
        pass
    return django_field_data


def update_django_many_to_many(
        django_model,
        django_id,
        django_many_to_many_params
):
    django_instance = django_model.objects.get(id=django_id)
    for param_name, many_to_many_objects in django_many_to_many_params.items():
        param = getattr(django_instance, param_name, None)
        if param is not None:
            param.clear()
            for obj in many_to_many_objects:
                param.add(obj)


@sync_to_async
def django_sync_to_async_list(
        django_func,
        params_to_use=None,
):
    if type(params_to_use) == dict:
        objects_qs = django_func(**params_to_use)
    else:
        objects_qs = django_func()

    result = list(objects_qs)

    return result


@sync_to_async
def django_sync_to_async_get(
        django_instance,
        param_to_get,
):
    param = getattr(django_instance, param_to_get)
    return param


def django_to_cache(
        redis_root,
        django_model,
        cache_conf,
):
    async def run_django_to_cache(
            redis_root,
            django_model,
            cache_conf,
    ):
        filter_by = cache_conf['filter_by']
        if filter_by:
            django_instances = await django_sync_to_async_list(django_model.objects.filter, filter_by)
        else:
            django_instances = await django_sync_to_async_list(django_model.objects.all)
        async_chunk_size = redis_root.async_db_requests_limit
        async_tasks = []
        completed = 0
        to_complete = len(django_instances)

        for django_instance in django_instances:
            async_tasks.append(
                update_or_create_redis_instance_from_django_instance(
                    redis_root,
                    django_instance,
                    cache_conf,
                )
            )
            completed += 1
            if len(async_tasks) == async_chunk_size or completed == to_complete:
                await asyncio.gather(*async_tasks)
                async_tasks = []
                print(
                    f'{datetime.datetime.now()} - '
                    f'Written {completed} {django_model} instances from django to cache')

        if cache_conf['delete']:
            async def check_if_need_to_delete_redis_instance(redis_root, django_instances_ids, redis_instance):
                if 'django_id' in redis_instance.keys():
                    if redis_instance['django_id'] not in django_instances_ids:
                        redis_root.delete(django_model, redis_instance)

            django_instances_ids = [django_instance.id for django_instance in django_instances]
            all_redis_instances = redis_root.get(django_model)
            async_tasks = [
                check_if_need_to_delete_redis_instance(redis_root, django_instances_ids, redis_instance)
                for redis_instance in all_redis_instances
            ]

            await asyncio.gather(*async_tasks)

        print(f'{datetime.datetime.now()} - '
              f'Deleted {django_model} instances from cache')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run_django_to_cache(
            redis_root,
            django_model,
            cache_conf,
        )
    )


async def update_or_create_redis_instance_from_django_instance(
        redis_root,
        django_instance,
        cache_conf,
):
    django_instance_model = django_instance.__class__
    old_redis_instance = redis_root.get(django_instance_model, django_id=django_instance.id)
    redis_dict = await django_instance_to_redis_params(
        redis_root,
        django_instance,
        cache_conf,
    )

    if not old_redis_instance:
        fields_to_create = redis_dict
        redis_instance = redis_root.create(
            django_model=django_instance_model,
            django_id=django_instance.id,
            **fields_to_create
        )
        result_redis_instance_id = redis_instance['id']
    else:
        old_redis_instance = old_redis_instance[0]
        fields_to_update = check_fields_need_to_update(
            old_redis_instance,
            redis_dict,
        )
        redis_root.update(django_instance_model, old_redis_instance,
                          **fields_to_update
                          )
        redis_instance = redis_root.get(django_instance_model, django_id=django_instance.id)[0]
        result_redis_instance_id = redis_instance['id']

    return result_redis_instance_id


def check_fields_need_to_update(
        redis_instance,
        redis_dict,
):
    fields_to_update = {}
    for field_name, field_value in redis_dict.items():
        if field_name not in redis_instance.keys():
            fields_to_update[field_name] = field_value
        else:
            if redis_instance[field_name] != field_value:
                fields_to_update[field_name] = field_value
    return fields_to_update


async def django_instance_field_to_redis_value(
        redis_root,
        django_instance,
        django_field,
        cache_conf,
):
    save_related_models = cache_conf['save_related_models']
    django_field_value = await django_sync_to_async_get(django_instance, django_field.name)
    redis_value = django_field_value
    if django_field.__class__ == django_models.ForeignKey:
        if django_field_value is None:
            redis_value = None
        else:
            django_foreign_key_instance = django_field_value
            if save_related_models:
                redis_foreign_key_instance = await get_or_create_redis_instance_from_django_instance(
                    django_foreign_key_instance,
                    redis_root,
                    cache_conf,
                )
                redis_value = redis_foreign_key_instance
            else:
                redis_value = django_foreign_key_instance.id
    elif django_field.__class__ == django_models.ManyToManyField:
        django_many_to_many_instances = await django_sync_to_async_list(django_field_value.all)
        if save_related_models:
            redis_value = [
                await get_or_create_redis_instance_from_django_instance(
                    django_many_to_many_instance,
                    redis_root,
                    cache_conf,
                )
                for django_many_to_many_instance in django_many_to_many_instances
            ]
        else:
            redis_value = [
                django_many_to_many_instance.id
                for django_many_to_many_instance in django_many_to_many_instances
            ]
    elif django_field.__class__.__name__.startswith('Image') or django_field.__class__.__name__.startswith('File'):
        try:
            redis_value = django_field_value.file.path
        except:
            redis_value = None
    return redis_value


async def django_instance_to_redis_params(
        redis_root,
        django_instance,
        cache_conf,
):
    redis_params = {}
    exclude_fields = cache_conf['exclude_fields']
    for i, django_field in enumerate(django_instance.__class__._meta.get_fields()):
        if not django_field.__class__.__name__.endswith('Rel'):
            django_field_name = django_field.name
            allowed = True
            if exclude_fields:
                allowed = (django_field.name not in exclude_fields)
            if allowed:
                if django_field.name not in ['id', 'pk']:
                    redis_param = await django_instance_field_to_redis_value(
                        redis_root,
                        django_instance,
                        django_field,
                        cache_conf,
                    )
                    if redis_param:
                        redis_params[django_field_name] = redis_param
    return redis_params


async def get_or_create_redis_instance_from_django_instance(
        django_instance,
        redis_root,
        cache_conf,
):
    django_instance_model = django_instance.__class__
    redis_instance = redis_root.get(django_instance_model, django_id=django_instance.id)
    if not redis_instance:
        redis_dict = await django_instance_to_redis_params(
            redis_root,
            django_instance,
            cache_conf,
        )
        redis_instance = redis_root.create(
            django_model=django_instance_model,
            django_id=django_instance.id,
            **redis_dict
        ).save()
    else:
        redis_instance = redis_instance[0]

    return redis_instance
