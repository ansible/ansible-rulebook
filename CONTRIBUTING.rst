.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/benthomasson/ansible_events/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

ansible-events could always use more documentation, whether as part of the
official ansible-events docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/benthomasson/ansible_events/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `ansible_events` for local development.

1. Fork the `ansible_events` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/ansible_events.git

3. We use a rules engine called Drools which is written in Java. From our python code
   we directly call the Drools Java classes using JPY. JPY needs Java to be installed on
   the machine. There are wheel distributions for JPY but they might not match your hardware
   so you would have to compile the JPY from source to get the package and shared object appropriate
   for your machine.
   To compile from Source you would need to set the following env var
   export PIP_NO_BINARY=jpy

   * Java 11+ installed
   * Environment variable JAVA_HOME set accordingly
   * Maven 3.8.1+ installed, might come bundled in some Java installs


4. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ cd ansible_events/
    $ python3.9 -m venv venv
    $ source venv/bin/activate
    $ pip install -e .
    $ pip install -r requirements_dev.txt
    $ ansible-galaxy collection install benthomasson.eda

5. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

6. When you're done making changes, check that your changes pass flake8 and the
   tests, including testing other Python versions with tox::

    $ flake8 ansible_events tests
    $ pytest
    $ tox

   To get flake8 and tox, just pip install them into your virtualenv.

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.

Git pre-commit hooks (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To automatically run linters and code formatter you may use
`git pre-commit hooks <https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks>`_.
This project provides a configuration for `pre-commit <https://pre-commit.com/>`_
framework to automatically setup hooks for you.

1. First install the ``pre-commit`` tool:

  a. Into your virtual environment:

     .. code-block:: console

         (venv) $ pip install pre-commit

  b. Into your user directory:

     .. code-block:: console

         $ pip install --user pre-commit

  c. Via ``pipx`` tool:

     .. code-block:: console

         $ pipx install pre-commit

2. Then generate git pre-commit hooks:

  .. code-block:: console

      $ pre-commit install

You may run pre-commit manually on all tracked files by calling:

.. code-block:: console

    $ pre-commit run --all-files


Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.9

Tips
----

To run a subset of tests::

$ pytest tests.test_ansible_events


Deploying
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

$ bump2version patch # possible: major / minor / patch
$ git push
$ git push --tags


Releasing
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed (including an entry in HISTORY.rst).
Then run::

$ python -m build
$ twine upload dist/*

