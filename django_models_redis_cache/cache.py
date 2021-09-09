import asyncio
import datetime

from asgiref.sync import sync_to_async
from django.db import models as django_models


def default_cache_func(
        django_model,
        redis_root,
        redis_model,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
        filter_by,
):
    redis_dicts = redis_root.get(redis_model, return_dict=True)
    cache_to_django(
        django_model,
        redis_dicts,
        redis_root,
    )
    django_to_cache(
        django_model,
        redis_model,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
        filter_by,
    )


def cache_to_django(django_model, redis_dicts, redis_root):
    async def run_cache_to_django(django_model, redis_dicts, redis_root):
        async_chunk_size = redis_root.async_db_requests_limit
        async_tasks = []
        completed = 0
        to_complete = len(redis_dicts.keys())

        for redis_instance_id, redis_instance_data in redis_dicts.items():
            async_tasks.append(
                update_or_create_django_instance_from_redis_instance(
                    redis_instance_data,
                    django_model,
                )
            )
            completed += 1
            if len(async_tasks) == async_chunk_size or completed == to_complete:
                await asyncio.gather(*async_tasks)
                async_tasks = []
                print(f'{datetime.datetime.now()} - Written {completed} {django_model.__name__} instances from cache to django')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cache_to_django(django_model, redis_dicts, redis_root))


async def update_or_create_django_instance_from_redis_instance(
        redis_instance,
        django_model,
):
    django_id = redis_instance['django_id']
    django_params, django_many_to_many_params = redis_dict_to_django_params(
        redis_instance,
        django_model
    )
    new_django_params = {}
    for k, v in django_params.items():
        if k != 'django_id':
            new_django_params[k] = v
    django_params = new_django_params
    django_instance = None
    if django_id != 'null':
        if django_model.objects.filter(id=django_id):
            django_instance = django_model.objects.filter(id=django_id).update(
                **django_params
            )
            update_django_many_to_many(
                django_model,
                django_id,
                django_many_to_many_params
            )
    if django_instance is None:
        django_instance = django_model.objects.create(
            **django_params
        )
        update_django_many_to_many(
            django_model,
            django_id,
            django_many_to_many_params
        )
    return django_instance


def redis_dict_to_django_params(
        redis_dict,
        django_model
):
    django_params = {}
    django_many_to_many_params = {}
    for django_field in django_model._meta.get_fields():
        django_field_name = django_field.name
        if django_field_name in redis_dict.keys():
            if django_field.__class__ == django_models.ForeignKey:
                foreign_key_model = django_field.remote_field.model
                redis_foreign_key_instance = redis_dict[django_field_name]
                django_foreign_key_instance = update_or_create_django_instance_from_redis_instance(
                    redis_foreign_key_instance,
                    foreign_key_model
                )
                django_params[django_field_name] = django_foreign_key_instance
            elif django_field.__class__ == django_models.ManyToManyField:
                many_to_many_model = django_field.remote_field.model
                django_many_to_many_instances = []
                redis_many_to_many_instances = redis_dict[django_field.name]
                for redis_many_to_many_instance in redis_many_to_many_instances:
                    django_many_to_many_instance = update_or_create_django_instance_from_redis_instance(
                        redis_many_to_many_instance,
                        many_to_many_model
                    )
                    django_many_to_many_instances.append(django_many_to_many_instance)
                django_many_to_many_params[django_field_name] = django_many_to_many_instances
            else:
                value = redis_dict[django_field.name]
                django_params[django_field_name] = value
    return django_params, django_many_to_many_params


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
    if params_to_use is None:
        result_qs = django_func()
    else:
        result_qs = django_func(**params_to_use)

    result = list(result_qs)

    return result


@sync_to_async
def django_sync_to_async_get(
        django_instance,
        param_to_get,
):
    param = getattr(django_instance, param_to_get)
    return param


def django_to_cache(
        django_model,
        redis_model,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
        filter_by,
):
    async def run_django_to_cache(
            django_model,
            redis_model,
            redis_root,
            save_related_models,
            get_or_create_redis_model_from_django_model,
            exclude_fields,
            filter_by,
    ):
        if filter_by.keys():
            if django_model in filter_by.keys():
                django_instances = await django_sync_to_async_list(django_model.objects.filter, filter_by[django_model])
            else:
                django_instances = await django_sync_to_async_list(django_model.objects.all)
        else:
            django_instances = await django_sync_to_async_list(django_model.objects.all)
        async_chunk_size = redis_root.async_db_requests_limit
        async_tasks = []
        completed = 0
        to_complete = len(django_instances)

        for django_instance in django_instances:
            async_tasks.append(
                update_or_create_redis_instance_from_django_instance(
                    django_instance,
                    redis_model,
                    redis_root,
                    save_related_models,
                    get_or_create_redis_model_from_django_model,
                    exclude_fields,
                )
            )
            completed += 1
            if len(async_tasks) == async_chunk_size or completed == to_complete:
                await asyncio.gather(*async_tasks)
                async_tasks = []
                print(f'{datetime.datetime.now()} - Written {completed} {django_model.__name__} instances from django to cache')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run_django_to_cache(
            django_model,
            redis_model,
            redis_root,
            save_related_models,
            get_or_create_redis_model_from_django_model,
            exclude_fields,
            filter_by,
        )
    )


async def update_or_create_redis_instance_from_django_instance(
        django_instance,
        redis_model,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
):
    redis_instance = redis_root.get(redis_model, django_id=django_instance.id)
    redis_dict = await django_instance_to_redis_params(
        django_instance,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
    )

    if not redis_instance:
        fields_to_create = redis_dict
        redis_instance = redis_model(
            redis_root=redis_root,
            django_id=django_instance.id,
            **fields_to_create
        ).save()
        result_redis_instance_id = redis_instance['id']
    else:
        redis_instance = redis_instance[0]
        fields_to_update = check_fields_need_to_update(
            redis_instance,
            redis_dict,
        )
        redis_root.update(redis_model, redis_instance,
                          **fields_to_update
                          )
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
        django_instance,
        django_field,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
):
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
                    save_related_models,
                    get_or_create_redis_model_from_django_model,
                    exclude_fields,
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
                    save_related_models,
                    get_or_create_redis_model_from_django_model,
                    exclude_fields,
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
        django_instance,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
):
    redis_params = {}
    django_model = django_instance.__class__
    for i, django_field in enumerate(django_instance.__class__._meta.get_fields()):
        if not django_field.__class__.__name__.endswith('Rel'):
            django_field_name = django_field.name
            allowed = True
            if django_model in exclude_fields.keys():
                allowed = (django_field_name not in exclude_fields[django_model])
            if allowed:
                if django_field.name not in ['id', 'pk']:
                    redis_param = await django_instance_field_to_redis_value(
                        django_instance,
                        django_field,
                        redis_root,
                        save_related_models,
                        get_or_create_redis_model_from_django_model,
                        exclude_fields,
                    )
                    if redis_param:
                        redis_params[django_field_name] = redis_param
    return redis_params


async def get_or_create_redis_instance_from_django_instance(
        django_instance,
        redis_root,
        save_related_models,
        get_or_create_redis_model_from_django_model,
        exclude_fields,
):
    django_instance_model = django_instance.__class__
    redis_model = get_or_create_redis_model_from_django_model(
        django_instance_model,
        redis_root,
        save_related_models,
        exclude_fields,
    )
    redis_instance = redis_root.get(redis_model, django_id=django_instance.id)
    if not redis_instance:
        redis_dict = await django_instance_to_redis_params(
            django_instance,
            redis_root,
            save_related_models,
            get_or_create_redis_model_from_django_model,
            exclude_fields,
        )
        redis_instance = redis_model(
            redis_root=redis_root,
            django_id=django_instance.id,
            **redis_dict
        ).save()
    else:
        redis_instance = redis_instance[0]

    return redis_instance
