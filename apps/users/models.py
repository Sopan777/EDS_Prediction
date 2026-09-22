from django.db import models

class UserAccount(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=128)
    email = models.CharField(max_length=128)
    role = models.CharField(max_length=64)
    department = models.CharField(max_length=64)
    permissions = models.CharField(max_length=64)
    initials = models.CharField(max_length=8)
    is_active = models.IntegerField(default=1)
    created_at = models.CharField(max_length=32)
    last_active = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        db_table = 'users'
        managed = False
        ordering = ['name']

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'department': self.department,
            'permissions': self.permissions,
            'initials': self.initials,
            'isActive': bool(self.is_active),
            'createdAt': self.created_at,
            'lastActive': self.last_active or 'Recently',
        }
