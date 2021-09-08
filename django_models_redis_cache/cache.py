from django.db import models as django_models


def default_cache_func(
        django_model,
        redis_root,
        get_or_create_redis_model_from_django_model
):
    redis_model = get_or_create_redis_model_from_django_model(django_model, redis_root)
    redis_dicts = redis_root.get(redis_model, return_dict=True)
    # cache_to_django(
    #     django_model,
    #     redis_dicts
    # )
    django_to_cache(
        django_model,
        redis_model,
        redis_root,
        get_or_create_redis_model_from_django_model
    )


def cache_to_django(django_model, redis_dicts):
    for redis_instance_id, redis_instance_data in redis_dicts.items():
        django_instance = update_or_create_django_instance_from_redis_instance(
            redis_instance_data,
            django_model,
        )


def update_or_create_django_instance_from_redis_instance(
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
        print(f'Added {django_instance.__class__.__name__}:{django_id} to django from cache')
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
                    redis_foreign_key_instance, foreign_key_model)
                django_params[django_field_name] = django_foreign_key_instance
            elif django_field.__class__ == django_models.ManyToManyField:
                many_to_many_model = django_field.remote_field.model
                django_many_to_many_instances = []
                redis_many_to_many_instances = redis_dict[django_field.name]
                for redis_many_to_many_instance in redis_many_to_many_instances:
                    django_many_to_many_instance = update_or_create_django_instance_from_redis_instance(
                        redis_many_to_many_instance, many_to_many_model)
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


def django_to_cache(
        django_model,
        redis_model,
        redis_root,
        get_or_create_redis_model_from_django_model
):
    for django_instance in django_model.objects.all():
        redis_instance = update_or_create_redis_instance_from_django_instance(
            django_instance,
            redis_model,
            redis_root,
            get_or_create_redis_model_from_django_model
        )


def update_or_create_redis_instance_from_django_instance(
        django_instance,
        redis_model,
        redis_root,
        get_or_create_redis_model_from_django_model
):
    redis_instance = redis_root.get(redis_model, django_id=django_instance.id)
    redis_dict = django_instance_to_redis_params(
        django_instance,
        redis_root,
        get_or_create_redis_model_from_django_model
    )

    if not redis_instance:
        redis_model(
            redis_root=redis_root,
            django_id=django_instance.id,
            **redis_dict
        ).save()
        print(f'Added {django_instance.__class__.__name__}:{django_instance.id} to cache from django')
    else:
        redis_instance = redis_instance[0]
        redis_root.update(redis_model, redis_instance,
                          django_id=django_instance.id,
                          **redis_dict
                          )

    result_redis_instance = redis_root.get(redis_model, django_id=django_instance.id)[0]
    return result_redis_instance


def django_instance_field_to_redis_value(
        django_instance,
        django_field,
        redis_root,
        get_or_create_redis_model_from_django_model
):

    django_field_value = getattr(django_instance, django_field.name)
    redis_value = django_field_value
    if django_field.__class__ == django_models.ForeignKey:
        if django_field_value is None:
            redis_value = None
        else:
            django_foreign_key_instance = django_field_value
            redis_value = get_or_create_redis_instance_from_django_instance(
                django_foreign_key_instance,
                redis_root,
                get_or_create_redis_model_from_django_model
            )

    elif django_field.__class__ == django_models.ManyToManyField:
        redis_value = [
            get_or_create_redis_instance_from_django_instance(
                django_many_to_many_instance,
                redis_root,
                get_or_create_redis_model_from_django_model
            )
            for django_many_to_many_instance in django_field_value.all()
        ]
    elif django_field.__class__.__name__.startswith('Image') or django_field.__class__.__name__.startswith('File'):
        try:
            redis_value = django_field_value.file.path
        except:
            redis_value = None
    return redis_value


def django_instance_to_redis_params(
        django_instance,
        redis_root,
        get_or_create_redis_model_from_django_model
):
    redis_params = {}
    for i, django_field in enumerate(django_instance.__class__._meta.get_fields()):
        if not django_field.__class__.__name__.endswith('Rel'):
            redis_param = django_instance_field_to_redis_value(
                django_instance,
                django_field,
                redis_root,
                get_or_create_redis_model_from_django_model
            )
            redis_params[django_field.name] = redis_param
    return redis_params


def get_or_create_redis_instance_from_django_instance(
        django_instance,
        redis_root,
        get_or_create_redis_model_from_django_model
):
    django_instance_model = django_instance.__class__
    redis_model = get_or_create_redis_model_from_django_model(django_instance_model, redis_root)
    redis_instance = redis_root.get(redis_model, django_id=django_instance.id)
    if not redis_instance:
        redis_dict = django_instance_to_redis_params(django_instance, redis_root, get_or_create_redis_model_from_django_model)
        redis_model(
            redis_root=redis_root,
            django_id=django_instance.id,
            **redis_dict
        ).save()
        redis_instance = redis_root.get(redis_model, django_id=django_instance.id)[0]
    else:
        redis_instance = redis_instance[0]

    return redis_instance
