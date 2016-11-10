import contextlib
from ctypes import c_char, sizeof, windll
import msvcrt
import os

from django.db import connection, transaction

sqlncli = windll.LoadLibrary('sqlncli11.dll')


class StreamingAPIFileDescriptor(object):

  SQL_FILESTREAM_READ = 0
  SQL_FILESTREAM_WRITE = 1
  SQL_FILESTREAM_READWRITE = 2

  def __init__(self, field, instance):
    self.field = field
    self.instance = instance
    self.cursor = connection.cursor()

  @contextlib.contextmanager
  def open(self, mode='rb'):
    with transaction.atomic():
      fs = self._open(mode)
      yield fs
      fs.close()

  def _get_open_flags(self, mode):
    flags = 0
    if 'r' in mode:
      flags |= os.O_RDONLY
    if 'b' in mode:
      flags |= os.O_BINARY
    else:
      flags |= os.O_TEXT
    if 'w' in mode:
      flags |= os.O_WRONLY
    if 'a' in mode:
      flags |= os.APPEND
    return flags

  def _get_sql_filestream_desired_access(self, mode):
    if '+' in mode:
      return self.SQL_FILESTREAM_READWRITE
    if 'r' in mode:
      return self.SQL_FILESTREAM_READ
    return self.SQL_FILESTREAM_WRITE

  def _open(self, mode='rb'):
    self.cursor.execute("""
SELECT %s.PathName() as filepath, GET_FILESTREAM_TRANSACTION_CONTEXT() as txContext
FROM %s
WHERE %s='%s'""" % (
      self.field.fs_field,
      self.instance._meta.model._meta.db_table,
      self.field.uuid_field,
      str(getattr(self.instance, self.field.uuid_field))))
    row = self.cursor.fetchone()
    filepath = '\\' + row[0].replace('\\\\', '\\')
    txContext = (c_char*len(row[1])).from_buffer_copy(row[1])
    fsHandle = sqlncli.OpenSqlFilestream(
        filepath,
        self._get_sql_filestream_desired_access(mode),
        0,
        txContext,
        sizeof(txContext),
        0
    )
    fsFileDescriptor = msvcrt.open_osfhandle(fsHandle, self._get_open_flags(mode))
    return os.fdopen(fsFileDescriptor, mode)


