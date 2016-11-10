=======================
django-mssql-filestream
=======================

This package provides necessary fields to use the SQL Server `Filestream <https://msdn.microsoft.com/fr-fr/library/gg471497.aspx>`_ feature.

Requires Django 1.7 and django-mssql 1.7.

This should be considered at very alpha stage. Suggestions / contributions welcome !

Quick start
-----------
.. code:: python

    import uuid

    from django.db import models
    from sql_filestream import FileStreamDataField, FileStreamField, UUIDField

    class DocumentModel(models.Model):
        doc_id = UUIDField(default=uuid.uuid4)
        doc_content = FileStreamDataField(null=True, blank=True)
        document = FileStreamField('doc_id', 'doc_content') # Virtual field (similar to the GenericForeignKey, if you are familiar with the ContentTypes app...)

T-SQL vs Win32 Streaming API
----------------------------
Direct file content manipulation with Transact-SQL can be done via the ``FileStreamDataField``.

.. code:: python

    # Create
    with open('some/file/path', 'rb') as f:
        doc_instance = DocumentModel.objects.create(doc_content=f.read())

    # Read
    content = doc_instance.doc_content # content is a django.core.files.base.ContentFile instance

    # Update
    doc_instance.doc_content = content
    doc_instance.save()


However, as stated in the filestream documentation, read / write operations should not generally be performed via T-SQL but instead by using the Win32 streaming API. This is what the ``FileStreamField`` is for.

.. code:: python

    from django.core.files.base import ContentFile

  # Create
  doc_instance = DocumentModel.objects.create()
  with open('some/file/path', 'rb') as f:
      doc_instance.document = ContentFile(f.read())


  # Read
  with doc_instance.document.open('rb') as f: # the FileStreamField provides a context manager that ensures that the read/write operations are performed within a transaction as needed by the Streaming API
      content = f.read()

  # Update
  with doc_instance.document.open('w') as f:
    f.write('test string')


Advised optimisations
---------------------

1. By default the ``object`` manager associated to your model selects all fields from it. As the ``FileStreamDataField`` contains the whole content of the file, you should defer this field by default in your querysets, for example by creating a custom manager like in this example:

.. code:: python

    from django.db import models

    class DocumentModelManager(models.Manager):

        def get_queryset(self):
            return super(DocumentModelManager, self).get_queryset().defer('doc_content')


    class DocumentModel(models.Model):
        ...

        objects = DocumentModelManager()


2. You can save the file directly via T-SQL when saving a new model instance, but it is more efficient to use the streaming API. This means you should first save the instance in database without setting its file content, then use the ``FileStreamField`` field of the model to save it via the streaming API. One solution is to override the model's ``save`` method. See this example:

.. code:: python

    def save(self, *args, **kwargs):
        content = None
        if not self.pk:
            content = self.doc_content
        super(DocumentModel, self).save(*args, **kwargs)
        with self.document.open('wb') as f:
            f.write(content)

