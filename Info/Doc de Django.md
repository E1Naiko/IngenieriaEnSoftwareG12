# Jerarquia de archivos de configuracion

fuente https://docs.djangoproject.com/en/6.1/intro/tutorial01/
```
djangotutorial/
    manage.py
    mysite/
        __init__.py
        settings.py
        urls.py
        asgi.py
        wsgi.py
```
stos archivos son:

    manage.py: Una utilidad de la línea de comandos que le permite interactuar con este proyecto Django de diferentes formas. Puede leer todos los detalles sobre manage.py en django-admin and manage.py.

    mysite/: A directory that is the actual Python package for your project. Its name is the Python package name you’ll need to use to import anything inside it (e.g. mysite.urls).

    mysite/__init__.py: Un archivo vacío que le indica a Python que este directorio debería ser considerado como un paquete Python. Si usted es un principiante lea más sobre los paquetes en la documentación oficial de Python.

    mysite/settings.py: Settings/configuration for this Django project. Django settings will tell you all about how settings work.

    mysite/urls.py: Las declaraciones URL para este proyecto Django; una «tabla de contenidos» de su sitio basado en Django. Puede leer más sobre las URLs en URL dispatcher.

    mysite/asgi.py: An entry-point for ASGI-compatible web servers to serve your project. See How to deploy with ASGI for more details.

    mysite/wsgi.py: Un punto de entrada para que los servidores web compatibles con WSGI puedan servir su proyecto. Consulte :doc:`/howto/deployment/wsgi/index`para más detalles.


---

# Crear Apps (ej: Polls)

Ahora que su entorno (un «proyecto») se ha configurado, ya está listo para empezar a trabajar.

Cada aplicación que usted escribe en Django consiste en un paquete de Python que sigue una determinada convención. Django tiene una utilidad que genera automáticamente la estructura básica de directorios de una aplicación, por lo que usted puede centrarse en la escritura de código en lugar de crear directorios.

Para crear su aplicación, asegúrese de que está en el mismo directorio que el archivo manage.py y escriba este comando:
/ 
```
$ python manage.py startapp polls
```
Esto creará un directorio polls, que se presenta de la siguiente manera:
```
polls/
    __init__.py
    admin.py
    apps.py
    migrations/
        __init__.py
    models.py
    tests.py
    views.py
```

El documento tambien explica el tema de los urls y la view mas basica que trae pero no lo voy a agregar

---