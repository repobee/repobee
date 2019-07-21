Cloning Repos in Bulk (the ``clone`` command)
*********************************************
It can at times be beneficial to be able to clone a bunch of student repos
at the same time. It could for example be prudent to do this slightly after
a deadline, as timestamps in a ``git`` commit can easily be altered (and are
therefore not particularly trustworthy). Whatever your reason may be, it's
very simple using the ``clone`` command. Again, assume that we have the
``students.txt`` file from :ref:`setup`, and that we want to clone all student
repos based on ``task-1`` and ``task-2``.

.. code-block:: bash

    $ repobee clone -mn task-1 task-2 -sf students.txt
    [INFO] cloning into student repos ...
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/slarse-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glassey-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glassey-task-2
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glennol-task-1
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/slarse-task-2
    [INFO] Cloned into https://some-enterprise-host/repobee-demo/glennol-task-2

Splendid! That's really all there is to the basic functionality, the repos
should now be in your current working directory. There is also a possibility to
run automated tasks on cloned repos, such as running test suites or linters. If
you're not satisfied with the tasks on offer, you can define your own. Read more
about it in the :ref:`plugins` section.

.. note::

   `For security reasons
   <https://github.blog/2012-09-21-easier-builds-and-deployments-using-buit-over-https-and-oauth/>`_,
   RepoBee doesn't actually use ``git clone`` to clone repositories. Instead,
   RepoBee clones by initializing the repository and running ``git pull``. The
   practical implication is that you can't simply enter a repository that's
   been cloned with RepoBee and run ``git pull`` to fetch updates. You will
   have to run ``repobee clone`` again in a different directory to fetch any
   updates students have made, alternatively simply delete to particular
   repositories you want to clone again and then run ``repobee clone``.
