import os
import django
from django.utils import timezone
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.local")
django.setup()

from plane.license.models import Instance, InstanceConfiguration

now = timezone.now()

try:
    instance = Instance.objects.get(pk=1)
    print('Instance already exists, updating...')
    instance.is_setup_done = True
    instance.save()
except Instance.DoesNotExist:
    instance = Instance.objects.create(
        instance_id=str(uuid.uuid4()),
        instance_name='SpecFlow Local',
        current_version='1.2.0',
        latest_version='1.2.0',
        last_checked_at=now,
        is_setup_done=True,
        is_telemetry_enabled=False,
    )
    print('Instance created:', instance.instance_id)

# Enable email password login
config, created = InstanceConfiguration.objects.update_or_create(
    key='IS_EMAIL_PASSWORD_LOGIN_ENABLED',
    defaults={'value': '1', 'is_encrypted': False}
)
print('Email auth enabled. Created:', created)

# Enable signup
config2, _ = InstanceConfiguration.objects.update_or_create(
    key='IS_SIGNUP_ENABLED',
    defaults={'value': '1', 'is_encrypted': False}
)
print('Signup enabled.')
print('Done!')
