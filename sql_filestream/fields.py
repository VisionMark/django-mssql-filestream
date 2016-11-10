import six
import uuid

from django.core import checks
from django.core.files.base import ContentFile, File
from django.db import models
from django.utils.six import with_metaclass

from sql_filestream.win32_streaming_api import StreamingAPIFileDescriptor


class FileStreamDataField(with_metaclass(models.SubfieldBase, models.BinaryField)):

  description = 'Field that maps to a SQL Server FILESTREAM column'
  unallowed_parameters = ['primary_key', 'upload_to', 'storage']

  def __init__(self, **kwargs):
    self.identifier_column = kwargs.get('identifier_column', 'doc_id')
    for arg in self.unallowed_parameters:
      setattr(self, '_%s_in_kwargs' % arg, arg in kwargs)
    super(FileStreamDataField, self).__init__(**kwargs)

  def check(self, **kwargs):
    errors = super(FileStreamDataField, self).check(**kwargs)
    errors.extend(self._check_unallowed_parameters())
    return errors

  def _check_unallowed_parameters(self):
    errors = []
    for arg in self.unallowed_parameters:
      if getattr(self, '_%s_in_kwargs' % arg):
        errors.append(
            checks.Error(
              "'%s' is not a valid argument for a %s." %
              (arg, self.__class__.__name__),
              obj=self
            )
        )
    return errors

  def _get_identifier_column(self):
    return self.identifier_column

  def db_type(self, connection):
    if connection.settings_dict['ENGINE'] == 'sqlserver_ado':
      return ('varbinary(max) FILESTREAM UNIQUE NONCLUSTERED ([%s] ASC)' %
          self.identifier_column)
    raise NotImplementedError('FileStreamField can only be used with '
        'sqlserver_ado database engine')

  def get_db_prep_value(self, value, connection, prepared=False):
    if isinstance(value, ContentFile):
      value = buffer(value.read())
    return super(FileStreamDataField, self).get_db_prep_value(value, connection,
        prepared)

  def to_python(self, value):
    if isinstance(value, ContentFile):
      return value
    return ContentFile(super(FileStreamDataField, self).to_python(value))


class FileStreamField(object):

  description = 'Virtual field to interact with the Win32 Streaming API'

  def __init__(self, uuid_field='file_id', fs_field='file_content'):
    self.uuid_field = uuid_field
    self.fs_field = fs_field
    self.editable = False
    self.rel = None
    self.column = None
    self._fd = None

  def contribute_to_class(self, cls, name):
    self.name = name
    self.model = cls
    cls._meta.add_virtual_field(self)
    setattr(cls, name, self)
    self.descriptor = None

  def __get__(self, instance, cls=None):
    if instance is None:
      return self
    if not instance.pk:
      return None
    if not self._fd:
      self._fd = StreamingAPIFileDescriptor(self, instance)
    return self._fd

  def __set__(self, instance, content):
    if not (isinstance(content, File) and content.closed == False):
      raise TypeError("'%s' must be an opened File instance."
        % self.name)
    if not instance.pk:
      # This means that the instance has not been saved to the database yet
      # In this case we cannot use the Win32 Streaming API to save the file
      raise IOError("Cannot write file via Streaming API for this instance, as "
          "it has not been saved to the database yet.")
    if not self._fd:
      self._fd = self.__get__(instance)
    with self._fd.open('wb') as f:
      for chunk in content:
        f.write(chunk)


# UUIDField has been added since Django 1.8 but is not supported yet by django-mssql
# So we create it here. The field maps to a SQL Server UNIQUEIDENTIFIER column
# Adapted from https://github.com/django/django/blob/master/django/db/models/fields/__init__.py#L2351
class UUIDField(with_metaclass(models.SubfieldBase, models.Field)):
  default_error_messages = {
      'invalid': "'%(value)s' is not a valid UUID.",
  }
  description = 'Universally unique identifier'
  empty_strings_allowed = False

  def __init__(self, verbose_name=None, **kwargs):
    kwargs['max_length'] = 32
    super(UUIDField, self).__init__(verbose_name, **kwargs)

  def deconstruct(self):
    name, path, args, kwargs = super(UUIDField, self).deconstruct()
    del kwargs['max_length']
    return name, path, args, kwargs

  def get_internal_type(self):
    return "UUIDField"

  def db_type(self, connection):
    return 'uniqueidentifier ROWGUIDCOL'

  def get_placeholder(self, value, connection):
    return 'CAST (%s as UNIQUEIDENTIFIER)'

  def get_db_prep_value(self, value, connection, prepared=False):
    if isinstance(value, uuid.UUID):
      return str(value)
    return value

  def to_python(self, value):
    if value and not isinstance(value, uuid.UUID):
      try:
        return uuid.UUID(value)
      except ValueError:
        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )
    return value
