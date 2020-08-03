from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin
)

# Create your models here.
class CustomUser (AbstractBaseUser, PermissionsMixin):
    pass