.. _tutorial-application:

The application
===============

Here is our application, cleverly written out in one go, as if by a
ninja.


``cloudlist.py``:

.. code-block:: python

    #!/usr/bin/env python
    from os import environ
    import flask
    from flask.ext.sqlalchemy import SQLAlchemy
    from flask.ext.script import Manager

    app = flask.Flask(__name__, template_folder='.')
    app.config.update({
        'DEBUG': bool(environ.get('DEBUG') == 'on'),
        'SQLALCHEMY_DATABASE_URI': environ.get('DATABASE'),
        'SECRET_KEY': environ.get('SECRET_KEY'),
    })

    db = SQLAlchemy(app)


    class Entry(db.Model):

        id = db.Column(db.Integer, primary_key=True)
        text = db.Column(db.String)


    @app.route('/', methods=['GET', 'POST'])
    def entry_list():
        if flask.request.method == 'POST':
            entry = Entry(text=flask.request.form['text'])
            db.session.add(entry)
            db.session.commit()
            flask.flash("Created entry %d" % entry.id)
            return flask.redirect(flask.url_for('entry_list'))
        return flask.render_template('entry_list.html', entry_list=Entry.query)


    @app.route('/<int:entry_id>/delete', methods=['POST'])
    def del_entry(entry_id):
        db.session.delete(Entry.query.get_or_404(entry_id))
        db.session.commit()
        flask.flash("Deleted entry %d" % entry_id)
        return flask.redirect(flask.url_for('entry_list'))


    manager = Manager(app)


    @manager.command
    def syncdb():
        db.create_all()


    if __name__ == '__main__':
        manager.run()


``entry_list.html``:

.. code-block:: html+jinja

    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Cloud List</title>
        <style>
          h1 { color: #1A8AE2; font-size: 22px; }
          li.entry > form { display: inline; }
          p.message { border: 1px solid #497214; color: #497214; background: #E9F3DC; }
        </style>
      </head>
      <body>

        {% for message in get_flashed_messages() %}
          <p class="message">{{ message }}</p>
        {% endfor %}

        <h1>Cloud List</h1>

        <ul>
        {% for entry in entry_list %}
          <li class="entry">
            {{ entry.text }}
            <form action="{{ url_for('del_entry', entry_id=entry.id) }}" method="post">
              <button type="submit">delete</button>
            </form>
          </li>
        {% endfor %}
        </ul>

        <form method="post">
          <label>New entry: <input name="text"></label>
          <button type="submit">create</button>
        </form>

      </body>
    </html>


``requirements.txt``::

    Werkzeug==0.8.3
    Jinja2==2.6
    Flask==0.9
    SQLAlchemy==0.8.0b2
    Flask-SQLAlchemy==0.16
    Flask-Script==0.5.3


``requirements-dev.txt``::

    Fabric==1.5.1
    honcho==0.2.0
    paramiko==1.9.0
    pycrypto==2.6


``Procfile``:

.. code-block:: bash

    web: python cloudlist.py runserver -p $PORT


There's a lot going on here so let's break it up into pieces.

We read options from environment variables.  That's how Airship is going
to provide configuration to our application, and, conveniently, that's
how you can provide configuration when running on your own computer. The
`Entry` model provides a good excuse to set up a database. Nowhere in
the application do we actually specify what database to use, it's
configured via the ``DATABASE`` environment variable.

The application has a couple of views, so we can see it working.  They
just provide CRUD for our model.  (Well, almost, since there's no
"update" action.)  After "create" and "delete" a `flash message`_ is
set.  The messages are stored in the browser session, and to have
working sessions, we need to set a random value for ``SECRET_KEY``.

`The pip documentation says`_ it's a good idea to list the application's
dependencies in a ``requirements.txt`` file.  Airship needs this file so
it can install the dependencies during deployment.
``requirements-dev.txt`` is completely ignored by Airship, the intention
is to install it manually in your development environment.  It provides
development tools: Honcho (runs the application) and Fabric (for
deploying to Airship).

Instead of just running the application (``app.run()``), we use
Flask-Script_, so we can implement a `syncdb` command, which creates the
`entry` database table.  The ``Procfile`` lists an application's process
types.  Ours has just one process type, the web service, and our
procfile describes how the process should be started.  In particular it
tells the app to listen on the port number provided by the environment.


.. _flash message: http://flask.pocoo.org/docs/patterns/flashing/
.. _The pip documentation says: http://www.pip-installer.org/en/latest/requirements.html
.. _Flask-Script: http://flask-script.readthedocs.org/


Continue with :ref:`tutorial-development`.
