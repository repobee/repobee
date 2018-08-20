Cloning Repos in Bulk (the ``clone`` command)
*********************************************
It can at times be beneficial to be able to clone a bunch of student repos
at the same time. It could for example be prudent to do this slighly after
a deadline, as timestamps in a ``git`` commit can easily be altered (and are
therefore not particularly trustworthy). Whatever your reason may be, it's
very simple using the ``clone`` command. Again, assume that we have the
``students.txt`` file from :ref:`setup`, and that we want to clone all student
repos based on ``master-repo-1`` and ``master-repo-2``.

.. code-block:: bash

    $ repomate clone -mn master-repo-1 master-repo-2 -sf students.txt
    [INFO] config file defaults:

       github_base_url: https://some-enterprise-host/api/v3
       user: slarse
       org_name: repomate-demo
       
    [INFO] cloning into student repos ...
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/spam-master-repo-1
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/ham-master-repo-1
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/ham-master-repo-2
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/eggs-master-repo-1
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/spam-master-repo-2
    [INFO] Cloned into https://some-enterprise-host/repomate-demo/eggs-master-repo-2

Splendid! That's really all there is to it, the repos should now be in your
current working directory.
